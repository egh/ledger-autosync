# Copyright (c) 2013-2021 Erik Hetzner
#
# This file is part of ledger-autosync
#
# ledger-autosync is free software: you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# ledger-autosync is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with ledger-autosync. If not, see
# <http://www.gnu.org/licenses/>.


import codecs
import csv
import logging

from ofxparse import OfxParser, OfxParserException

from ledgerautosync.converter import CsvConverter


class Synchronizer(object):
    def __init__(self, lgr):
        self.lgr = lgr


class OfxSynchronizer(Synchronizer):
    def __init__(self, lgr, hardcodeaccount=None, shortenaccount=None):
        self.hardcodeaccount = hardcodeaccount
        self.shortenaccount = shortenaccount
        super(OfxSynchronizer, self).__init__(lgr)

    @staticmethod
    def parse_file(path):
        with open(path, "rb") as ofx_file:
            return OfxParser.parse(ofx_file)

    def is_txn_synced(self, acctid, txn):
        if self.lgr is None:
            # User called with --no-ledger
            # All transactions are considered "synced" in this case.
            return False
        else:
            acctid_to_use = acctid
            txnid_to_use = txn.id
            if self.hardcodeaccount:
                acctid_to_use = self.hardcodeaccount
                txnid_to_use = txnid_to_use.replace(acctid, acctid_to_use)
            elif self.shortenaccount:
                acctid_to_use = acctid[-4:]
                txnid_to_use = txnid_to_use.replace(acctid, acctid_to_use)
            ofxid = "%s.%s" % (acctid_to_use, txnid_to_use)
            return self.lgr.check_transaction_by_id("ofxid", ofxid)

    # Filter out comment transactions. These have an amount of 0 and the same
    # datetime as the previous transactions.
    def filter_comment_txns(self, txns):
        last_txn = None
        retval = []
        for txn in txns:
            if (
                (last_txn is not None)
                and hasattr(txn, "amount")
                and (txn.amount == 0)
                and hasattr(last_txn, "date")
                and hasattr(txn, "date")
                and (last_txn.date == txn.date)
            ):
                # This is a comment transaction
                pass
            else:
                last_txn = txn
                retval.append(txn)
        return retval

    @staticmethod
    def extract_sort_key(txn):
        if hasattr(txn, "tradeDate"):
            return txn.tradeDate
        elif hasattr(txn, "date"):
            return txn.date
        elif hasattr(txn, "settleDate"):
            return txn.settleDate
        return None

    def filter(self, txns, acctid):
        if len(txns) == 0:
            sorted_txns = txns
        else:
            sorted_txns = sorted(txns, key=OfxSynchronizer.extract_sort_key)
        retval = [txn for txn in sorted_txns if not (self.is_txn_synced(acctid, txn))]
        return self.filter_comment_txns(retval)

    def get_new_txns(self, acct, max_days=999999, resync=False):
        if resync or (max_days < 7):
            days = max_days
        else:
            days = 7
        last_txns_len = 0
        while True:
            logging.debug(
                "Downloading %d days of transactions for %s (max_days=%d)."
                % (days, acct.description, max_days)
            )
            raw = acct.download(days=days)

            if raw.read() == "Server error occured.  Received HttpStatusCode of 400":
                raise Exception("Error connecting to account %s" % (acct.description))
            raw.seek(0)
            ofx = None
            try:
                ofx = OfxParser.parse(raw)
            except OfxParserException as ex:
                if ex.message == "The ofx file is empty!":
                    return (ofx, [])
                else:
                    raise ex
            if ofx.signon is not None:
                if ofx.signon.severity == "ERROR":
                    raise Exception(
                        "Error returned from server for %s: %s"
                        % (acct.description, ofx.signon.message)
                    )
            if not (hasattr(ofx, "account")):
                # some banks return this for no txns
                if days >= max_days:
                    logging.debug("Hit max days.")
                    # return None to let the caller know that we don't
                    # even have account info
                    return (None, None)
                else:
                    days = days * 2
                    if days > max_days:
                        days = max_days
                    logging.debug("empty account: increasing days ago to %d." % (days))
                    last_txns_len = 0
            else:
                txns = ofx.account.statement.transactions
                new_txns = self.filter(txns, ofx.account.account_id)
                logging.debug("txns: %d" % (len(txns)))
                logging.debug("new txns: %d" % (len(new_txns)))
                if (len(txns) > 0) and (last_txns_len == len(txns)):
                    # not getting more txns than last time; we have
                    # reached the beginning
                    logging.debug("Not getting more txns than last time, done.")
                    return (ofx, new_txns)
                elif (len(txns) > len(new_txns)) or (days >= max_days):
                    # got more txns than were new or hit max_days, we've
                    # reached a stopping point
                    if days >= max_days:
                        logging.debug("Hit max days.")
                    else:
                        logging.debug("Got some stale txns.")
                    return (ofx, new_txns)
                else:
                    # all txns were new, increase how far back we go
                    days = days * 2
                    if days > max_days:
                        days = max_days
                    logging.debug("Increasing days ago to %d." % (days))
                    last_txns_len = len(txns)


class CsvSynchronizer(Synchronizer):
    def __init__(self, lgr, payee_format=None, date_format=None):
        super(CsvSynchronizer, self).__init__(lgr)
        self.payee_format = payee_format
        self.date_format = date_format

    def is_row_synced(self, converter, row):
        if self.lgr is None:
            # User called with --no-ledger
            # All transactions are considered "synced" in this case.
            return False
        else:
            return self.lgr.check_transaction_by_id("csvid", converter.get_csv_id(row))

    def parse_file(self, path, accountname=None, unknownaccount=None):
        with open(path) as f:
            has_bom = f.read(3) == codecs.BOM_UTF8
            if not (has_bom):
                f.seek(0)
            else:
                f.seek(3)
            dialect = csv.Sniffer().sniff(f.readline())
            if not (has_bom):
                f.seek(0)
            else:
                f.seek(3)
            dialect.skipinitialspace = True
            reader = csv.DictReader(f, dialect=dialect)
            converter = CsvConverter.make_converter(
                set(reader.fieldnames),
                dialect,
                ledger=self.lgr,
                name=accountname,
                unknownaccount=unknownaccount,
                payee_format=self.payee_format,
                date_format=self.date_format,
            )
            # Create a new reader in case the converter modified the dialect
            if not (has_bom):
                f.seek(0)
            else:
                f.seek(3)
            reader = csv.DictReader(f, dialect=dialect)
            return [
                converter.convert(row)
                for row in reader
                if not (self.is_row_synced(converter, row))
            ]

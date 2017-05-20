# Copyright (c) 2013, 2014 Erik Hetzner
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

from __future__ import absolute_import
from ofxparse import OfxParser
from ledgerautosync.converter import CsvConverter
from ofxparse.ofxparse import InvestmentTransaction
import logging
import csv

class Synchronizer(object):
    def __init__(self, lgr):
        self.lgr = lgr

class OfxSynchronizer(Synchronizer):
    def __init__(self, lgr):
        super(OfxSynchronizer, self).__init__(lgr)

    def parse_file(self, path, accountname=None):
        ofx = OfxParser.parse(file(path))
        return (ofx, self.filter(ofx))

    def is_txn_synced(self, acctid, txn):
        if self.lgr is None:
            # User called with --no-ledger
            # All transactions are considered "synced" in this case.
            return False
        else:
            ofxid = "%s.%s" % (acctid, txn.id)
            return self.lgr.check_transaction_by_id("ofxid", ofxid)

    # Filter out comment transactions. These have an amount of 0 and the same
    # datetime as the previous transactions.
    def filter_comment_txns(self, txns):
        last_txn = None
        retval = []
        for txn in txns:
            if (last_txn is not None) and \
               hasattr(txn, 'amount') and \
               (txn.amount == 0) and \
               hasattr(last_txn, 'date') and \
               hasattr(txn, 'date') and \
               (last_txn.date == txn.date):
                # This is a comment transaction
                pass
            else:
                last_txn = txn
                retval.append(txn)
        return retval

    def filter(self, ofx):
        def extract_sort_key(txn):
            if hasattr(txn, 'tradeDate'):
                return txn.tradeDate
            elif hasattr(txn, 'date'):
                return txn.date
            elif hasattr(txn, 'settleDate'):
                return txn.settleDate
            return None
        txns = ofx.account.statement.transactions
        if len(txns) == 0:
            sorted_txns = txns
        else:
            sorted_txns = sorted(txns, key=extract_sort_key)
        acctid = ofx.account.account_id
        retval = [txn for txn in sorted_txns
                  if not(self.is_txn_synced(acctid, txn))]
        return self.filter_comment_txns(retval)

    def get_new_txns(self, acct, max_days=999999, resync=False):
        if resync or (max_days < 7):
            days = max_days
        else:
            days = 7
        last_txns_len = 0
        while (True):
            logging.debug(
                "Downloading %d days of transactions for %s (max_days=%d)." % (
                    days, acct.description, max_days))
            raw = acct.download(days=days)

            if raw.read() == 'Server error occured.  Received HttpStatusCode of 400':
                raise Exception("Error connecting to account %s"%(acct.description))
            raw.seek(0)
            ofx = OfxParser.parse(raw)
            if not(hasattr(ofx, 'account')):
                # some banks return this for no txns
                if (days >= max_days):
                    logging.debug("Hit max days.")
                    # return None to let the caller know that we don't
                    # even have account info
                    return (None, None)
                else:
                    days = days * 2
                    if (days > max_days):
                        days = max_days
                    logging.debug(
                        "empty account: increasing days ago to %d." % (days))
                    last_txns_len = 0
            else:
                txns = ofx.account.statement.transactions
                new_txns = self.filter(ofx)
                logging.debug("txns: %d" % (len(txns)))
                logging.debug("new txns: %d" % (len(new_txns)))
                if ((len(txns) > 0) and (last_txns_len == len(txns))):
                    # not getting more txns than last time; we have
                    # reached the beginning
                    logging.debug("Not getting more txns than last time, done.")
                    return (ofx, new_txns)
                elif (len(txns) > len(new_txns)) or (days >= max_days):
                    # got more txns than were new or hit max_days, we've
                    # reached a stopping point
                    if (days >= max_days):
                        logging.debug("Hit max days.")
                    else:
                        logging.debug("Got some stale txns.")
                    return (ofx, new_txns)
                else:
                    # all txns were new, increase how far back we go
                    days = days * 2
                    if (days > max_days):
                        days = max_days
                    logging.debug("Increasing days ago to %d." % (days))
                    last_txns_len = len(txns)


class CsvSynchronizer(Synchronizer):
    def __init__(self, lgr):
        super(CsvSynchronizer, self).__init__(lgr)

    def parse_file(self, path, accountname=None, unknownaccount=None):
        with open(path, 'rb') as f:
            dialect = csv.Sniffer().sniff(f.read(1024))
            f.seek(0)
            dialect.skipinitialspace = True
            reader = csv.DictReader(f, dialect=dialect)
            converter = CsvConverter.make_converter(
                reader,
                name=accountname,
                ledger=self.lgr,
                unknownaccount=unknownaccount)
            return [converter.convert(row)
                    for row in reader
                    if not(self.lgr.check_transaction_by_id(
                            "csvid", converter.get_csv_id(row)))]

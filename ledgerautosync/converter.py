# Copyright (c) 2013, 2014 Erik Hetzner
# Portions Copyright (c) 2016 James S Blachly, MD
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
from decimal import Decimal
import re
from ofxparse.ofxparse import Transaction as OfxTransaction, InvestmentTransaction
from ledgerautosync import EmptyInstitutionException
import datetime
import hashlib

AUTOSYNC_INITIAL = "autosync_initial"
ALL_AUTOSYNC_INITIAL = "all.%s" % (AUTOSYNC_INITIAL)

class SecurityList(object):
    """
    The SecurityList represents the OFX <SECLIST>...</SECLIST>
    and holds securities present in the OFX records

    <SECINFO>...</SECINFO> as implemented by OFXparse only includes:
    {memo, name, ticker, uniqueid}
    Unfortunately does not provide uniqueid_type or currency

    It is iterable, and also provides lookup table (LUT) functionality
    provides __next__() for Py3
    """
    def __init__(self, securities):
        self.cusip_lut = dict()
        self.ticker_lut = dict()

        self._iter = iter(securities)
        self.securities = securities
        if len(securities) == 0: return

        # index
        for sec in securities:
            # unfortunately OFXparse does not currently implement
            # security.uniqueid_type so I am presuming here
            if sec.uniqueid: self.cusip_lut[sec.uniqueid] = sec
            if sec.ticker:   self.ticker_lut[sec.ticker]  = sec
            # This indexing strategy (whereby I index the object instead of
            # the inverse value (e.g. ticker symbol) directly has a flaw
            # in that an OFX file could define a security list section and
            # list CUSIPs without ticker property, or the converse

    def __iter__(self):
        return self

    def __next__(self):         # Py3 iterable
        return next(self._iter)

    def next(self):             # Python 2
        return next(self._iter)

    def __len__(self):
        return len(self.securities)

    # one possibility is to just implement __getitem__(),
    # however since OFXparse does not implement securitylist.security.uniqueid_type
    # I'll have no idea if what I am seeing is a CUSISP
    # unless I look it up specifically as a CUSIP (and it exists)
    def find_cusip(self, cusip):
        if cusip in self.cusip_lut: return self.cusip_lut[cusip]
        else: return None

    def find_ticker(self, ticker):
        if ticker in self.ticker_lut: return self.ticker_lut[ticker]
        else: return None


class Transaction(object):
    def __init__(self, date, payee, postings, cleared=False, metadata={}, aux_date=None):
        self.date = date
        self.aux_date = aux_date
        self.payee = payee
        self.postings = postings
        self.metadata = metadata
        self.cleared = cleared

    def format(self, indent=4):
        retval = ""
        cleared_str = " "
        if self.cleared:
            cleared_str = " * "
        aux_date_str = ""
        if self.aux_date is not None:
            aux_date_str = "=%s"%(self.aux_date.strftime("%Y/%m/%d"))
        retval += "%s%s%s%s\n"%(self.date.strftime("%Y/%m/%d"), aux_date_str, cleared_str, self.payee)
        for k,v in self.metadata.iteritems():
            retval += "%s; %s: %s\n" % (" "*indent, k, v)
        for posting in self.postings:
            retval += posting.format(indent)
        return retval

class Posting(object):
    def __init__(self, account, amount, asserted=None, unit_price=None):
        self.account = account
        self.amount = amount
        self.asserted = asserted
        self.unit_price = unit_price

    def format(self, indent=4):
        space_count = 65 - indent - len(self.account) - len(self.amount.format())
        if space_count < 2:
            space_count = 2
        retval = "%s%s%s%s" % (
            " " * indent, self.account, " "*space_count, self.amount.format())
        if self.asserted is not None:
            retval = "%s = %s"%(retval, self.asserted.format())
        if self.unit_price is not None:
            retval = "%s @ %s"%(retval, self.unit_price.format())
        return "%s\n"%(retval)

class Amount(object):
    def __init__(self, number, currency, reverse=False, unlimited=False):
        self.number = Decimal(number)
        self.reverse = reverse
        self.unlimited = unlimited
        self.currency = currency

    def format(self):
        # Commodities must be quoted in ledger if they have
        # whitespace or numerals.
        if re.search(r'[\s0-9]', self.currency):
            currency = "\"%s\"" % (self.currency)
        else:
            currency = self.currency
        if self.unlimited:
            number = str(abs(self.number))
        else:
            number = "%0.2f" % (abs(self.number))
        if self.number.is_signed() != self.reverse:
            prefix = "-"
        else:
            prefix = ""
        if len(currency) == 1:
            # $ comes before
            return "%s%s%s" % (prefix, currency, number)
        else:
            # USD comes after
            return "%s%s %s" % (prefix, number, currency)


class Converter(object):
    @staticmethod
    def clean_id(id):
        return id.replace('/', '_').\
            replace('$', '_').\
            replace(' ', '_').\
            replace('@', '_').\
            replace('*', '_').\
            replace('[', '_').\
            replace(']', '_')

    def __init__(self, ledger=None, unknownaccount=None, currency='$', indent=4):
        self.lgr = ledger
        self.indent = indent
        self.unknownaccount = unknownaccount
        self.currency = currency.upper()
        if self.currency == "USD":
            self.currency = "$"

    def mk_dynamic_account(self, payee, exclude):
        if self.lgr is None:
            return self.unknownaccount or 'Expenses:Misc'
        else:
            account = self.lgr.get_account_by_payee(payee, exclude)
            if account is None:
                return self.unknownaccount or 'Expenses:Misc'
            else:
                return account


class OfxConverter(Converter):
    def __init__(self, ofx, name, indent=4, ledger=None, fid=None,
                 unknownaccount=None):
        super(OfxConverter, self).__init__(ledger=ledger,
                                           indent=indent,
                                           unknownaccount=unknownaccount,
                                           currency=ofx.account.statement.currency)
        self.acctid = ofx.account.account_id
        # build SecurityList (including indexing by CUSIP and ticker symbol)
        if hasattr(ofx, 'security_list') and ofx.security_list is not None:
            self.security_list = SecurityList(ofx.security_list)
        else:
            self.security_list = SecurityList([])

        if fid is not None:
            self.fid = fid
        else:
            if ofx.account.institution is None:
                raise EmptyInstitutionException(
                    "Institution provided by OFX is empty and no fid supplied!")
            else:
                self.fid = ofx.account.institution.fid
        self.name = name

    def mk_ofxid(self, txnid):
        return Converter.clean_id("%s.%s.%s" % (self.fid, self.acctid, txnid))

    def format_payee(self, txn):
        payee = None
        memo = None
        if (hasattr(txn, 'payee')):
            payee = txn.payee
        if (hasattr(txn, 'memo')):
            memo = txn.memo

        if (payee is None or payee == '') and (memo is None or memo == ''):
            retval = "%s: %s"%(self.name, txn.type)
            if txn.type == 'transfer' and hasattr(txn, 'tferaction'):
                retval += ": %s"%(txn.tferaction.lower())
            return retval
        if (payee is None or payee == '') or txn.memo.startswith(payee):
            return memo
        elif (memo is None or memo == '') or payee.startswith(memo):
            return payee
        else:
            return "%s %s" % (payee, memo)

    def format_balance(self, statement):
        # Get date. Ensure the date is a date-like object.
        if (hasattr(statement, 'balance_date') and
            hasattr(statement.balance_date, 'strftime')):
            date = statement.balance_date
        elif (hasattr(statement, 'end_date') and
              hasattr(statement.end_date, 'strftime')):
            date = statement.end_date
        else:
            return ""
        if (hasattr(statement, 'balance')):
            return Transaction(
                date=date,
                cleared=True,
                payee="--Autosync Balance Assertion",
                postings=[
                    Posting(
                        self.name,
                        Amount(Decimal("0"), currency=self.currency),
                        asserted=Amount(statement.balance, self.currency))
                ]).format(self.indent)
        else:
            return ""

    def format_initial_balance(self, statement):
        if (hasattr(statement, 'balance')):
            initbal = statement.balance
            for txn in statement.transactions:
                initbal -= txn.amount
            return Transaction(
                date=statement.start_date,
                payee="--Autosync Initial Balance",
                cleared=True,
                postings=[
                    Posting(
                        self.name,
                        Amount(initbal, currency=self.currency)).format(self.indent),
                    Posting(
                        "Assets:Equity",
                        Amount(initbal, currency=self.currency, reverse=True)).format(self.indent)
                    ],
                metadata={ "ofxid": self.mk_ofxid(AUTOSYNC_INITIAL) }
            ).format(self.indent)
        else:
            return ""

    # Return the ticker symbol of the security with CUSIP, if it exists in the
    # security_list mapping. Otherwise, simply return the CUSIP.
    def maybe_get_ticker(self, cusip):
        security = self.security_list.find_cusip(cusip)
        if security is not None:
            return security.ticker
        else:
            return cusip

    def convert(self, txn):
        """
        Convert an OFX Transaction to a posting
        """

        ofxid = self.mk_ofxid(txn.id)

        if isinstance(txn, OfxTransaction):
            return Transaction(
                date=txn.date,
                payee=self.format_payee(txn),
                metadata={"ofxid": ofxid},
                postings=[
                    Posting(
                        self.name,
                        Amount(txn.amount, self.currency)
                    ),
                    Posting(
                        self.mk_dynamic_account(self.format_payee(txn), exclude=self.name),
                        Amount(txn.amount, self.currency, reverse=True)
                    )]
            )
        elif isinstance(txn, InvestmentTransaction):
            acct1 = self.name
            acct2 = self.name

            posting1 = None
            posting2 = None

            metadata = {"ofxid": ofxid}

            security = self.maybe_get_ticker(txn.security)

            if isinstance(txn.type, basestring):
                # recent versions of ofxparse
                if re.match('^(buy|sell)', txn.type):
                    acct2 = self.unknownaccount or 'Assets:Unknown'
                elif txn.type == 'transfer':
                    acct2 = 'Transfer'
                elif txn.type == 'reinvest':
                    # reinvestment of income
                    # TODO: make this configurable
                    acct2 = 'Income:Interest'
                elif txn.type == 'income' and txn.income_type == 'DIV':
                    # Fidelity lists non-reinvested dividend income as
                    # type: income, income_type: DIV
                    # TODO: determine how dividend income is listed from other institutions
                    # income/DIV transactions do not involve buying or selling a security
                    # so their postings need special handling compared to others
                    metadata['dividend_from'] = security
                    acct2 = 'Income:Dividends'
                    posting1 = Posting( acct1,
                                        Amount(txn.total, self.currency))
                    posting2 = Posting( acct2,
                                        Amount(txn.total, self.currency, reverse=True ))
                else:
                    # ???
                    pass
            else:
                # Old version of ofxparse
                if (txn.type in [0, 1, 3, 4]):
                    # buymf, sellmf, buystock, sellstock
                    acct2 = self.unknownaccount or 'Assets:Unknown'
                elif (txn.type == 2):
                    # reinvest
                    acct2 = 'Income:Interest'
                else:
                    # ???
                    pass

            aux_date = None
            if txn.settleDate is not None and \
               txn.settleDate != txn.tradeDate:
                aux_date = txn.settleDate

            # income/DIV already defined above;
            # this block defines all other posting types
            if posting1 is None and posting2 is None:
                posting1 = Posting(acct1,
                                Amount(txn.units, security, unlimited=True),
                                unit_price=Amount(txn.unit_price, self.currency, unlimited=True))
                posting2 = Posting(acct2,
                                Amount(txn.units * txn.unit_price, self.currency, reverse=True))
            else:
                # Previously defined if type:income income_type/DIV
                pass

            return Transaction(
                date=txn.tradeDate,
                aux_date=txn.settleDate,
                payee=self.format_payee(txn),
                metadata=metadata,
                postings=[ posting1, posting2 ]
            )

    def format_position(self, pos):
        if hasattr(pos, 'date') and hasattr(pos, 'security') and \
           hasattr(pos, 'unit_price'):
            dateStr = pos.date.strftime("%Y/%m/%d %H:%M:%S")
            return "P %s %s %s\n" % (dateStr, self.maybe_get_ticker(pos.security), pos.unit_price)


class CsvConverter(Converter):
    @staticmethod
    def make_converter(csv, name=None, **kwargs):
        fieldset = set(csv.fieldnames)
        for klass in CsvConverter.__subclasses__():
            if klass.FIELDSET <= fieldset:
                return klass(csv, name=name, **kwargs)
        # Found no class, bail
        raise Exception('Cannot determine CSV type')

    # By default, return an MD5 of the key-value pairs in the row.
    # If a better ID is available, should be overridden.
    def get_csv_id(self, row):
        h = hashlib.md5()
        for key in sorted(row.keys()):
            h.update("%s=%s\n"%(key, row[key]))
        return h.hexdigest()

    def __init__(self, csv, name=None, indent=4, ledger=None, unknownaccount=None):
        super(CsvConverter, self).__init__(
            ledger=ledger,
            indent=indent,
            unknownaccount=unknownaccount)
        self.name = name
        self.csv = csv


class PaypalConverter(CsvConverter):
    FIELDSET = set(['Currency', 'Date', 'Gross', 'Item Title', 'Name', 'Net', 'Status', 'To Email Address', 'Transaction ID', 'Type'])

    def __init__(self, *args, **kwargs):
        super(PaypalConverter, self).__init__(*args, **kwargs)

    def get_csv_id(self, row):
        return "paypal.%s"%(Converter.clean_id(row['Transaction ID']))

    def convert(self, row):
        if (((row['Status'] != "Completed") and (row['Status'] != "Refunded") and (row['Status'] != "Reversed")) or (row['Type'] == "Shopping Cart Item")):
            return ""
        else:
            currency = row['Currency']
            if row['Type'] == "Add Funds from a Bank Account" or row['Type'] == "Charge From Debit Card":
                postings=[
                    Posting(
                        self.name,
                        Amount(Decimal(row['Net']), currency)
                    ),
                    Posting(
                        "Transfer:Paypal",
                        Amount(Decimal(row['Net']), currency, reverse=True)
                    )]
            else:
                postings=[
                    Posting(
                        self.name,
                        Amount(Decimal(row['Gross']), currency)
                    ),
                    Posting(
                        # TODO Our payees are breaking the payee search in mk_dynamic_account
                        "Expenses:Misc", #self.mk_dynamic_account(payee, exclude=self.name),
                        Amount(Decimal(row['Gross']), currency, reverse=True)
                    )]
            return Transaction(
                date=datetime.datetime.strptime(row['Date'], "%m/%d/%Y"),
                payee=re.sub(
                    r"\s+", " ",
                    "%s %s %s ID: %s, %s"%(row['Name'], row['To Email Address'], row['Item Title'], row['Transaction ID'], row['Type'])),
                metadata={"csvid": self.get_csv_id(row)},
                postings=postings)


class AmazonConverter(CsvConverter):
    FIELDSET = set(['Currency', 'Title', 'Order Date', 'Order ID'])

    def __init__(self, *args, **kwargs):
        super(AmazonConverter, self).__init__(*args, **kwargs)

    def mk_amount(self, row, reverse=False):
        currency = row['Currency']
        if currency == "USD": currency = "$"
        return Amount(Decimal(re.sub(r"\$", "", row['Item Total'])), currency, reverse=reverse)

    def get_csv_id(self, row):
        return "amazon.%s"%(Converter.clean_id(row['Order ID']))

    def convert(self, row):
        return Transaction(
            date=datetime.datetime.strptime(row['Order Date'], "%m/%d/%y"),
            payee=row['Title'],
            metadata={
                "url": "https://www.amazon.com/gp/css/summary/print.html/ref=od_aui_print_invoice?ie=UTF8&orderID=%s"%(row['Order ID']),
                "csvid": self.get_csv_id(row)},
            postings=[
                Posting(self.name, self.mk_amount(row)),
                Posting("Expenses:Misc", self.mk_amount(row, reverse=True))
            ])

class MintConverter(CsvConverter):
    FIELDSET = set(['Date', 'Amount', 'Description', 'Account Name', 'Category', 'Transaction Type'])

    def __init__(self, *args, **kwargs):
        super(MintConverter, self).__init__(*args, **kwargs)

    def mk_amount(self, row, reverse=False):
        return Amount(Decimal(row['Amount']), '$', reverse=reverse)

    def convert(self, row):
        account = self.name
        if account is None:
            account = row['Account Name']
        postings = []
        if (row['Transaction Type'] == 'credit'):
            postings = [Posting(account, self.mk_amount(row, reverse=True)),
                        Posting(row['Category'], self.mk_amount(row))]
        else:
            postings = [Posting(account, self.mk_amount(row)),
                        Posting("Expenses:%s"%(row['Category']), self.mk_amount(row, reverse=True))]

        return Transaction(
            date=datetime.datetime.strptime(row['Date'], "%m/%d/%Y"),
            metadata={"csvid": "mint.%s"%(self.get_csv_id(row))},
            payee=row['Description'],
            postings=postings)

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
from decimal import Decimal
import re
from ofxparse.ofxparse import Transaction as OfxTransaction, InvestmentTransaction
from ledgerautosync import EmptyInstitutionException
import datetime

AUTOSYNC_INITIAL = "autosync_initial"
ALL_AUTOSYNC_INITIAL = "all.%s" % (AUTOSYNC_INITIAL)


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
        space_count = 52 - indent - len(self.account) - len(self.amount.format())
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
        self.number = number
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
            replace('@', '_')

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
    def __init__(self, account, name, indent=4, ledger=None, fid=None,
                 unknownaccount=None):
        super(OfxConverter, self).__init__(ledger=ledger,
                                           indent=indent,
                                           unknownaccount=unknownaccount,
                                           currency=account.statement.currency)
        self.acctid = account.account_id
        if fid is not None:
            self.fid = fid
        else:
            if account.institution is None:
                raise EmptyInstitutionException(
                    "Institution provided by OFX is empty and no fid supplied!")
            else:
                self.fid = account.institution.fid
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
                retval += ": %s"%(txn.tferaction)
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

    def convert(self, txn):
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
            if isinstance(txn.type, str):
                # recent versions of ofxparse
                if re.match('^(buy|sell)', txn.type):
                    acct2 = self.unknownaccount or 'Assets:Unknown'
                elif txn.type == 'transfer':
                    acct2 = 'Transfer'
                elif txn.type == 'reinvest':
                    # reinvestment of income
                    # TODO: make this configurable
                    acct2 = 'Income:Interest'
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
            return Transaction(
                date=txn.tradeDate,
                aux_date=txn.settleDate,
                payee=self.format_payee(txn),
                metadata={"ofxid": ofxid},
                postings=[
                    Posting(
                        acct1,
                        Amount(txn.units, txn.security, unlimited=True),
                        unit_price=Amount(txn.unit_price, self.currency, unlimited=True)),
                    Posting(
                        acct2,
                        Amount(txn.units * txn.unit_price, self.currency, reverse=True)
                    )]
            )

    def format_position(self, pos):
        if hasattr(pos, 'date') and hasattr(pos, 'security') and \
           hasattr(pos, 'unit_price'):
            dateStr = pos.date.strftime("%Y/%m/%d %H:%M:%S")
            return "P %s %s %s\n" % (dateStr, pos.security, pos.unit_price)


class CsvConverter(Converter):
    @staticmethod
    def make_converter(csv, name=None, **kwargs):
        fieldset = set(csv.fieldnames)
        for klass in CsvConverter.__subclasses__():
            if klass.FIELDSET <= fieldset:
                return klass(csv, name=name, **kwargs)
        # Found no class, bail
        raise Exception('Cannot determine CSV type')

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

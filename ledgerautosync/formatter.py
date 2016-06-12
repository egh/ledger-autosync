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
from ofxparse.ofxparse import Transaction, InvestmentTransaction
from ledgerautosync import EmptyInstitutionException
import datetime

AUTOSYNC_INITIAL = "autosync_initial"
ALL_AUTOSYNC_INITIAL = "all.%s" % (AUTOSYNC_INITIAL)


class Formatter(object):
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

    def format_txn_line(self, acct, amt, suffix=""):
        space_count = 52 - self.indent - len(acct) - len(amt)
        if space_count < 2:
            space_count = 2
        return "%s%s%s%s%s\n" % (
            " " * self.indent, acct, " "*space_count, amt, suffix)

    def format_amount(self, amount, reverse=False, unlimited=False,
                      currency=None):
        if currency is None:
            currency = self.currency
        # Commodities must be quoted in ledger if they have
        # whitespace or numerals.
        if re.search(r'[\s0-9]', currency):
            currency = "\"%s\"" % (currency)
        if unlimited:
            amt = str(abs(amount))
        else:
            amt = "%0.2f" % (abs(amount))
        if amount.is_signed() != reverse:
            prefix = "-"
        else:
            prefix = ""
        if len(currency) == 1:
            # $ comes before
            return "%s%s%s" % (prefix, currency, amt)
        else:
            # USD comes after
            return "%s%s %s" % (prefix, amt, currency)

    def format_date(self, date):
        return date.strftime("%Y/%m/%d")

    def mk_dynamic_account(self, payee, exclude):
        if self.lgr is None:
            return self.unknownaccount or 'Expenses:Misc'
        else:
            account = self.lgr.get_account_by_payee(payee, exclude)
            if account is None:
                return self.unknownaccount or 'Expenses:Misc'
            else:
                return account


class OfxFormatter(Formatter):
    def __init__(self, account, name, indent=4, ledger=None, fid=None,
                 unknownaccount=None):
        super(OfxFormatter, self).__init__(ledger=ledger,
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
        return Formatter.clean_id("%s.%s.%s" % (self.fid, self.acctid, txnid))

    def format_payee(self, txn):
        payee = None
        memo = None
        if (hasattr(txn, 'payee')):
            payee = txn.payee
        if (hasattr(txn, 'memo')):
            memo = txn.memo

        if (payee is None or payee == '') and (memo is None or memo == ''):
            return "UNKNOWN"
        if (payee is None or payee == '') or txn.memo.startswith(payee):
            return memo
        elif (memo is None or memo == '') or payee.startswith(memo):
            return payee
        else:
            return "%s %s" % (payee, memo)

    def format_balance(self, statement):
        retval = ""
        # Get date. Ensure the date is a date-like object.
        if (hasattr(statement, 'balance_date') and
            hasattr(statement.balance_date, 'strftime')):
            date = statement.balance_date
        elif (hasattr(statement, 'end_date') and
              hasattr(statement.end_date, 'strftime')):
            date = statement.end_date
        else:
            return retval
        if (hasattr(statement, 'balance')):
            retval += "%s * --Autosync Balance Assertion\n" % \
                      (self.format_date(date))
            retval += self.format_txn_line(
                self.name,
                self.format_amount(Decimal("0")),
                " = %s" % (self.format_amount(statement.balance)))
        return retval

    def format_initial_balance(self, statement):
        retval = ""
        if (hasattr(statement, 'balance')):
            initbal = statement.balance
            for txn in statement.transactions:
                initbal -= txn.amount
            retval += "%s * --Autosync Initial Balance\n" % (
                self.format_date(statement.start_date))
            retval += "%s; ofxid: %s\n" % (" " * self.indent,
                                           self.mk_ofxid(AUTOSYNC_INITIAL))
            retval += self.format_txn_line(self.name,
                                           self.format_amount(initbal))
            retval += self.format_txn_line(
                "Assets:Equity",
                self.format_amount(initbal, reverse=True))
        return retval

    def format_txn(self, txn):
        retval = ""
        ofxid = self.mk_ofxid(txn.id)
        if isinstance(txn, Transaction):
            retval += "%s %s\n" % (
                self.format_date(txn.date), self.format_payee(txn))
            retval += "%s; ofxid: %s\n" % (" "*self.indent, ofxid)
            retval += self.format_txn_line(
                self.name, self.format_amount(txn.amount))
            retval += self.format_txn_line(
                self.mk_dynamic_account(self.format_payee(txn), exclude=self.name),
                self.format_amount(txn.amount, reverse=True))
        elif isinstance(txn, InvestmentTransaction):
            acct1 = self.name
            acct2 = self.name
            if isinstance(txn.type, str):
                # recent versions of ofxparse
                if re.match('^(buy|sell)', txn.type):
                    acct2 = self.unknownaccount or 'Assets:Unknown'
                elif txn.type == 'transfer' or txn.type == 'jrnlsec':
                    # both sides are the same, internal transfer
                    pass
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
            if txn.settleDate is not None and \
               txn.settleDate != txn.tradeDate:
                retval = "%s=%s %s\n" % (
                    txn.tradeDate.strftime("%Y/%m/%d"),
                    txn.settleDate.strftime("%Y/%m/%d"),
                    self.format_payee(txn))
            else:
                retval = "%s %s\n" % (
                    txn.tradeDate.strftime("%Y/%m/%d"),
                    self.format_payee(txn))
            retval += "%s; ofxid: %s\n" % (" "*self.indent, ofxid)
            retval += self.format_txn_line(
                acct=acct1,
                amt=self.format_amount(txn.units, currency=txn.security, unlimited=True),
                suffix=" @ %s" % (self.format_amount(txn.unit_price, unlimited=True)))
            retval += self.format_txn_line(
                acct=acct2,
                amt=self.format_amount(txn.units * txn.unit_price, reverse=True))
        return retval

    def format_position(self, pos):
        if hasattr(pos, 'date') and hasattr(pos, 'security') and \
           hasattr(pos, 'unit_price'):
            dateStr = pos.date.strftime("%Y/%m/%d %H:%M:%S")
            return "P %s %s %s\n" % (dateStr, pos.security, pos.unit_price)


class CsvFormatter(Formatter):
    PAYPAL_FIELDS = ["Date", "Time", "Time Zone", "Name", "Type", "Status", "Currency", "Gross", "Fee", "Net", "From Email Address", "To Email Address", "Transaction ID", "Counterparty Status", "Shipping Address", "Address Status", "Item Title", "Item ID", "Shipping and Handling Amount", "Insurance Amount", "Sales Tax", "Option 1 Name", "Option 1 Value", "Option 2 Name", "Option 2 Value", "Auction Site", "Buyer ID", "Item URL", "Closing Date", "Escrow Id", "Invoice Id", "Reference Txn ID", "Invoice Number", "Custom Number", "Receipt ID", "Balance", "Contact Phone Number", ""]

    def __init__(self, name, csv, indent=4, ledger=None, unknownaccount=None):
        super(CsvFormatter, self).__init__(
            ledger=ledger,
            indent=indent,
            unknownaccount=unknownaccount)
        self.name = name
        self.csv = csv
        if sorted(self.csv.fieldnames) == sorted(self.PAYPAL_FIELDS):
            self.csv_type = "paypal"
        else:
            raise Exception('Cannot determine CSV type')

    def mk_csv_id_line(self, txn_id):
        return "%s; csvid: %s.%s\n" % (" " * self.indent,
                                       self.csv_type,
                                       Formatter.clean_id(txn_id))

    def format_txn(self, row):
        retval = ""
        d = datetime.datetime.strptime(row['Date'], "%m/%d/%Y")
        payee = "%s %s %s ID: %s, %s"%(row['Name'], row['To Email Address'], row['Item Title'], row['Transaction ID'], row['Type'])
        retval += "%s %s\n"%(self.format_date(d), re.sub(r"\s+", " ", payee))
        currency = row['Currency']
        if (((row['Status'] != "Completed") and (row['Status'] != "Refunded") and (row['Status'] != "Reversed")) or (row['Type'] == "Shopping Cart Item")):
            return ""
        retval += self.mk_csv_id_line(row['Transaction ID'])
        if row['Type'] == "Add Funds from a Bank Account" or row['Type'] == "Charge From Debit Card":
            retval += self.format_txn_line(
                self.name,
                self.format_amount(Decimal(row['Net']), currency=currency))
            retval += self.format_txn_line(
                "Transfer:Paypal",
                self.format_amount(Decimal(row['Net']), currency=currency, reverse=True))
        else:
            retval += self.format_txn_line(
                self.name,
                self.format_amount(Decimal(row['Gross']), currency=currency))
            retval += self.format_txn_line(
                "Transfer:Paypal",
                self.format_amount(Decimal(row['Gross']), currency=currency, reverse=True))
        return retval

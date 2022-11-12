# ledger-autosync plugin for CSV files from N26, a Berlin-based online bank.

import datetime
from decimal import Decimal
import re

from ledgerautosync.converter import Amount, Converter, CsvConverter, Posting, Transaction

class N26Converter(CsvConverter):
    FIELDSET = set(["Date","Payee","Account number","Transaction type","Payment reference","Amount (EUR)",
                    "Amount (Foreign Currency)","Type Foreign Currency","Exchange Rate"])

    def __init__(self, *args, **kwargs):
        super(N26Converter, self).__init__(*args, **kwargs)

    def mk_currency(self, currency):
        if currency == "USD":
            currency = "$"
        elif currency == "GBP":
            currency = "£"
        elif currency == "EUR":
            currency = "€"
        return currency

    def mk_amount(self, amt, currency, reverse=False):
        currency = self.mk_currency(currency)
        return Amount(
            Decimal(amt), currency, reverse=reverse
        )

    def convert(self, row):
        amt = Decimal(row["Amount (EUR)"])
        if amt < 0:
            reverse   = False
            acct_from = self.name
            curr_from = self.mk_currency("EUR")
            acct_to   = "Expenses:Misc"
            curr_to   = self.mk_currency(row["Type Foreign Currency"] or "EUR")
        else:
            reverse   = True
            acct_from = "Assets:Other"
            curr_from = self.mk_currency(row["Type Foreign Currency"] or "EUR")
            acct_to   = self.name
            curr_to   = self.mk_currency("EUR")
        amt_from = Amount(amt, curr_from, reverse=reverse)
        amt_to   = Amount(amt, curr_to,   reverse=not reverse)

        payee = re.sub(r"[A-Za-z]+('[A-Za-z]+)?",lambda word: word.group(0).capitalize(),row["Payee"])
        meta = {"csvid": self.get_csv_id(row)}

        posting_from = Posting(acct_from, amt_from, metadata=meta if acct_from == self.name else {})
        posting_to   = Posting(acct_to,   amt_to,   metadata=meta if acct_to   == self.name else {})

        return Transaction(
            date=datetime.datetime.strptime(row["Date"], "%Y-%m-%d"),
            cleared=True,
            date_format="%Y-%m-%d",
            payee=payee,
            postings=[posting_to, posting_from]
        )

# ledger-autosync plugin for CSV files from Revolut, a Lithuania-based online bank.

import datetime
from decimal import Decimal
import re

from ledgerautosync.converter import Amount, Converter, CsvConverter, Posting, Transaction

class RevolutConverter(CsvConverter):
    FIELDSET = set(["Type","Product","Started Date","Completed Date",
        "Description","Amount","Fee","Currency","State","Balance"])

    def __init__(self, *args, **kwargs):
        super(RevolutConverter, self).__init__(*args, **kwargs)

    def mk_currency(self, currency):
        if currency == "USD":
            currency = "$"
        elif currency == "GBP":
            currency = "£"
        elif currency == "EUR":
            currency = "€"
        return currency

    def convert(self, row):
        amt = Decimal(row["Amount"])
        currency = self.mk_currency(row["Currency"])
        cleared = row["State"] == "COMPLETED"
        if row["Type"] == "TOPUP":
            reverse   = True
            acct_from = "Assets:Other"
            amt_from  = Amount(amt, currency, reverse=reverse)
            acct_to   = self.name
            amt_to    = Amount(amt, currency, reverse=not reverse)
        else:
            reverse   = False
            acct_from = self.name
            amt_from  = Amount(amt, currency, reverse=reverse)
            acct_to   = "Expenses:Misc"
            amt_to    = Amount(amt, currency, reverse=not reverse)

        payee = row["Description"]
        meta = {"csvid": self.get_csv_id(row)}

        posting_from = Posting(acct_from, amt_from, metadata=meta if acct_from == self.name else {})
        posting_fee  = Posting("Expenses:Bank Charges", Amount(Decimal(row["Fee"]), currency, reverse=True)) if row["Fee"] != "0.00" else None
        posting_to   = Posting(acct_to,   amt_to,   metadata=meta if acct_to   == self.name else {})

        date     = datetime.datetime.strptime(row["Started Date"], "%Y-%m-%d %H:%M:%S")
        aux_date = datetime.datetime.strptime(row["Completed Date"], "%Y-%m-%d %H:%M:%S") if row["Completed Date"] else None
        if date.date() == aux_date.date():
            aux_date = None

        postings = [posting_to, posting_from]
        if posting_fee:
            postings.append(posting_fee)
            postings.append(posting_fee.clone_inverted(self.name))
        return Transaction(
            date=date,
            cleared=cleared,
            aux_date=aux_date,
            date_format="%Y-%m-%d",
            payee=payee,
            postings=postings
        )

# ledger-autosync plugin for CSV files from First Direct, a UK bank.
# The currency is fixed to GBP for that reason.

import datetime
import re

from ledgerautosync.converter import Amount, CsvConverter, Posting, Transaction


class SomeConverter(CsvConverter):
    FIELDSET = set(["Date", "Description", "Amount"])

    def __init__(self, *args, **kwargs):
        super(SomeConverter, self).__init__(*args, **kwargs)

    def convert(self, row):
        amount = row["Amount"]
        return Transaction(
            date=datetime.datetime.strptime(row["Date"], "%d/%m/%Y"),
            payee=row["Description"].strip(),
            postings=[
                Posting(self.name, Amount(amount, "GBP")),
                Posting(self.unknownaccount, Amount(amount, "GBP", reverse=True)),
            ],
        )

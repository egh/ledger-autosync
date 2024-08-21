# ledger-autosync plugin for CSV files from AIB, an Irish bank.

import datetime
from decimal import Decimal
import re

from ledgerautosync.converter import (
    Amount,
    Converter,
    CsvConverter,
    Posting,
    Transaction,
)


class AIBConverter(CsvConverter):
    FIELDSET = set(
        [
            "Posted Account",
            "Posted Transactions Date",
            "Description",
            "Debit Amount",
            "Credit Amount",
            "Balance",
            "Transaction Type",
        ]
    )

    def __init__(self, *args, **kwargs):
        super(AIBConverter, self).__init__(*args, **kwargs)

    def convert(self, row):
        meta = {"csvid": self.get_csv_id(row)}
        debit = Decimal(row["Debit Amount"]) if row["Debit Amount"] else None
        credit = Decimal(row["Credit Amount"]) if row["Credit Amount"] else None
        if debit and debit > 0:
            posting_from = Posting(
                self.name, Amount(debit, "€", reverse=True), metadata=meta
            )
            posting_to = posting_from.clone_inverted("Expenses:Misc")
        elif credit and credit > 0:
            posting_from = Posting("Assets:Other", Amount(credit, "€", reverse=True))
            posting_to = posting_from.clone_inverted(self.name, metadata=meta)
        else:
            return ""

        payee = re.sub(
            r"[A-Za-z]+('[A-Za-z]+)?",
            lambda word: word.group(0).capitalize(),
            row["Description"],
        )

        return Transaction(
            date=datetime.datetime.strptime(
                row["Posted Transactions Date"], "%d/%m/%y"
            ),
            cleared=True,
            date_format="%Y-%m-%d",
            payee=payee,
            postings=[posting_to, posting_from],
        )

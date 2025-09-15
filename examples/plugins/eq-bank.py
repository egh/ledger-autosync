#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Devin Davis

from ledgerautosync.converter import CsvConverter, Posting, Transaction, Amount
import datetime
import re
import hashlib

class EQBankConverter(CsvConverter):
    FIELDSET = set(["Transfer date", "Description", "Amount", "Balance"])

    def __init__(self, *args, **kwargs):
        super(EQBankConverter, self).__init__(*args, **kwargs)

    def convert(self, row):
        if not row or not row.get("Transfer date") or not row.get("Description") or not row.get("Amount"):
            return None

        try:
            trans_date = datetime.datetime.strptime(row["Transfer date"], "%d %b %Y")
        except ValueError:
            return None

        amount_match = re.match(r"^(-?)\$([0-9,\.]+)", row["Amount"])
        if not amount_match:
            return None
        amount = amount_match.group(2).replace(",", "")
        reverse = amount_match.group(1) == "-"

        payee = row["Description"].strip()

        description = row["Description"].lower()

        contra_account = "Expenses:Misc"

        unique_string = f"{row['Transfer date']}{row['Description']}{row['Amount']}"
        csvid = hashlib.md5(unique_string.encode('utf-8')).hexdigest()

        return Transaction(
            date=trans_date,
            payee=payee,
            postings=[
                Posting(self.name, Amount(amount, '$', reverse=reverse)),
                Posting(contra_account, Amount(amount, '$', reverse=not reverse))
            ],
            metadata={"csvid": csvid}
        )

# ledger-autosync plugin for CSV files from Wise, formerly TransferWise.

# You must download and sync a CSV statement for all currencies that
# cover the same time period.  Since Wise lists the transactions in
# reverse chronological order, you might want to run with --reverse flag.
# The code assumes some text is in English.  Adjust mk_currency() and
# anything else to suit. No warranty, YMMV, etc.

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


class WiseConverter(CsvConverter):
    FIELDSET = set(
        [
            "TransferWise ID",
            "Date",
            "Amount",
            "Currency",
            "Description",
            "Payment Reference",
            "Running Balance",
            "Exchange From",
            "Exchange To",
            "Exchange Rate",
            "Payer Name",
            "Payee Name",
            "Payee Account Number",
            "Merchant",
            "Card Last Four Digits",
            "Card Holder Full Name",
            "Attachment",
            "Note",
            "Total fees",
        ]
    )

    def __init__(self, *args, **kwargs):
        super(WiseConverter, self).__init__(*args, **kwargs)

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
        return Amount(Decimal(amt), currency, reverse=reverse)

    def convert(self, row):
        tid = row["TransferWise ID"]
        checknum = int(tid.split("-")[1])
        amt = Decimal(row["Amount"])
        acct_from = self.name
        curr_from = self.mk_currency(row["Currency"])
        acct_to = "Expenses:Misc"
        curr_to = curr_from
        amt_from = Amount(amt, curr_from)
        amt_to = Amount(amt, curr_to, reverse=True)

        fee_not_included = (
            tid.startswith("CARD-") and row["Currency"] == "USD" and row["Exchange To"]
        )

        if row["Exchange To"]:
            rate = Decimal(row["Exchange Rate"])
            curr = self.mk_currency(row["Currency"])
            curr_from = self.mk_currency(row["Exchange From"])
            curr_to = self.mk_currency(row["Exchange To"])
            if curr == curr_from:
                amt_from = Amount(amt, curr_from)
                # Card transactions from USD to other currencies do not consider the fees in the exchange rate
                amt_to = Amount(
                    (
                        amt
                        + (
                            Decimal(row["Total fees"])
                            if tid.startswith("CARD-")
                            and not (row["Currency"] == "USD" and row["Exchange To"])
                            else Decimal(0)
                        )
                    )
                    * rate,
                    curr_to,
                    reverse=True,
                )
                acct_from = self.name
            else:
                # Do not import this exchange from this statement; instead use the statement for the matching "from" currency
                if tid.startswith("BALANCE-"):
                    return ""
                amt_from = Amount(amt / rate, curr_from, reverse=True)
                amt_to = Amount(amt, curr_to)
                acct_from = self.name if tid.startswith("BALANCE-") else "Expenses:Misc"
                if tid.startswith("BALANCE-"):
                    acct_to = self.name

        if row["Description"].startswith("Wise Charges for:"):
            acct_to = "Expenses:Bank Charges"

        if tid.startswith("TRANSFER-"):
            payee = row["Payee Name"] or row["Payer Name"]
        elif tid.startswith("BALANCE-"):
            payee = row["Description"]
        else:
            payee = row["Merchant"]

        meta = {"csvid": self.get_csv_id(row)}

        posting_from = Posting(acct_from, amt_from, metadata=meta)
        posting_to = Posting(acct_to, amt_to)

        return Transaction(
            date=datetime.datetime.strptime(row["Date"], "%d-%m-%Y"),
            cleared=True,
            date_format="%Y-%m-%d",
            checknum=checknum,
            payee=payee,
            postings=[posting_to, posting_from],
        )

    def get_csv_id(self, row):
        fmt = (
            "wise.fee.{}"
            if row["Description"].startswith("Wise Charges for:")
            else "wise.{}"
        )
        return fmt.format(Converter.clean_id(row["TransferWise ID"]))

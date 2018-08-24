# ledger-autosync plugin for CSV files from First Direct, a UK bank.
# The currency is fixed to GBP for that reason.

from ledgerautosync.converter import CsvConverter, Posting, Transaction, Amount
import datetime
import re

class SomeConverter(CsvConverter):
    FIELDSET = set(["Date","Description","Amount","Balance"])

    def __init__(self, *args, **kwargs):
        super(SomeConverter, self).__init__(*args, **kwargs)

    def convert(self, row):
        amount = row['Amount']
        if amount.startswith('-'):
            reverse = True
        else:
            reverse = False
        return Transaction(
            date=datetime.datetime.strptime(row['Date'], "%d/%m/%Y"),
            payee=row['Description'],
            postings=[Posting(self.name, Amount(amount, 'GBP', reverse=reverse)),
                      Posting(self.unknownaccount, Amount(amount, 'GBP', reverse=not(reverse)))])

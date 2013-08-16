import datetime
import time
from ofxclient.config import OfxConfig
import argparse
from ofxclient.client import Client
from formatter import Formatter
from ledgerautosync.sync import Synchronizer

def run(ledger, config):
    sync = Synchronizer(ledger)
    for acct in config.accounts():
        (ofx, txns) = sync.get_new_txns(acct)
        formatter = Formatter(currency=ofx.account.statement.currency, name=acct.description)
        for txn in txns:
            print formatter.format_txn(txn)

if __name__ == '__main__':
    ledger = Ledger()
    config = OfxConfig()
    run(ledger, config)

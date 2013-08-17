import datetime
import time
from ofxclient.config import OfxConfig
import argparse
from ofxclient.client import Client
from formatter import Formatter
from ledgerautosync.sync import Synchronizer
from ledgerautosync.ledger import Ledger
import logging

def run(ledger, config, max_days=90, resync=False):
    sync = Synchronizer(ledger)
    for acct in config.accounts():
        (ofx, txns) = sync.get_new_txns(acct, resync=resync, max_days=max_days)
        formatter = Formatter(acctid=ofx.account.account_id, currency=ofx.account.statement.currency, name=acct.description)
        for txn in txns:
            print formatter.format_txn(txn)

def run_default():
    logging.basicConfig(level=logging.DEBUG)

    parser = argparse.ArgumentParser(description='Synchronize ledger.')
    parser.add_argument('-m', '--max', dest='max_days', type=int, default=90,
                        help='maximum number of days to process')
    parser.add_argument('-r', '--resync', dest='resync', type=bool, default=False,
                        help='do not stop until max days reached')
    parser.add_argument('-a', '--account', dest='account_name', type=str, default=None,
                        help='set account name for import')
    args = parser.parse_args()
    ledger = Ledger()
    config = OfxConfig()
    run(ledger, config, max_days=args.max_days, min_days=args.min_days)

if __name__ == '__main__':
    run_default()

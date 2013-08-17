import datetime
import time
from ofxclient.config import OfxConfig
from ofxparse import OfxParser
import argparse
from ofxclient.client import Client
from formatter import Formatter
from ledgerautosync.sync import Synchronizer
from ledgerautosync.ledger import Ledger
import logging

def sync(ledger, config, max_days=90, resync=False):
    sync = Synchronizer(ledger)
    for acct in config.accounts():
        (ofx, txns) = sync.get_new_txns(acct, resync=resync, max_days=max_days)
        formatter = Formatter(acctid=ofx.account.account_id, currency=ofx.account.statement.currency, name=acct.description)
        for txn in txns:
            print formatter.format_txn(txn)

def import_ofx(ledger, path, accountname=None):
    sync = Synchronizer(ledger)
    (ofx, txns) = sync.parse_file(path)
    if accountname is None:
        accountname = "%s:%s"%(ofx.account.institution.organization, ofx.account.account_id)
    formatter = Formatter(acctid=ofx.account.account_id, currency=ofx.account.statement.currency, name=accountname)
    for txn in txns:
        print formatter.format_txn(txn)
        
def run():
    logging.basicConfig(level=logging.DEBUG)

    parser = argparse.ArgumentParser(description='Synchronize ledger.')
    parser.add_argument('-m', '--max', dest='max_days', type=int, default=90,
                        help='maximum number of days to process')
    parser.add_argument('-r', '--resync', action='store_true', default=False,
                        help='do not stop until max days reached')
    parser.add_argument('PATH', nargs='?', help='do not sync; import from OFX file')
    parser.add_argument('-a', '--account', dest='account_name', type=str, default=None,
                        help='set account name for import')
    args = parser.parse_args()
    ledger = Ledger()
    if args.PATH is None:
        config = OfxConfig()
        sync(ledger, config, max_days=args.max_days, resync=args.resync)
    else:
        import_ofx(ledger, args.PATH, args.account_name)

if __name__ == '__main__':
    run()

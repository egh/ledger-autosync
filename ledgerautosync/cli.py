#!/usr/bin/env python
import datetime
import time
from ofxclient.config import OfxConfig
from ofxparse import OfxParser
import argparse
from ofxclient.client import Client
from formatter import Formatter
from ledgerautosync.sync import Synchronizer
from ledgerautosync.ledger import mk_ledger, Ledger, HLedger
import logging
import sys
import traceback

def sync(ledger, config, max_days=90, resync=False, indent=4):
    sync = Synchronizer(ledger)
    for acct in config.accounts():
        try:
            (ofx, txns) = sync.get_new_txns(acct, resync=resync, max_days=max_days)
            formatter = Formatter(account=ofx.account, name=acct.description, ledger=ledger, indent=indent)
            for txn in reversed(txns):
                print formatter.format_txn(txn)
        except:
            sys.stderr.write("Caught exception processing %s"%(acct.description))
            traceback.print_exc(file=sys.stderr)
                             
def import_ofx(ledger, path, accountname=None, indent=4):
    sync = Synchronizer(ledger)
    (ofx, txns) = sync.parse_file(path)
    if accountname is None:
        accountname = "%s:%s"%(ofx.account.institution.organization, ofx.account.account_id)
    formatter = Formatter(account=ofx.account, name=accountname, ledger=ledger, indent=indent)
    for txn in txns:
        print formatter.format_txn(txn)
        
def run(args=None):
    if args is None: args = sys.argv[1:]

    parser = argparse.ArgumentParser(description='Synchronize ledger.')
    parser.add_argument('-m', '--max', type=int, default=90,
                        help='maximum number of days to process')
    parser.add_argument('-r', '--resync', action='store_true', default=False,
                        help='do not stop until max days reached')
    parser.add_argument('PATH', nargs='?', help='do not sync; import from OFX file')
    parser.add_argument('-a', '--account', type=str, default=None,
                        help='set account name for import')
    parser.add_argument('-l', '--ledger', type=str, default=None,
                        help='specify ledger file to READ for syncing')
    parser.add_argument('-i', '--indent', type=int, default=4,
                        help='number of spaces to use for indentation')
    parser.add_argument('-d', '--debug', action='store_true', default=False,
                        help='enable debug logging')
    parser.add_argument('--hledger', action='store_true', default=False,
                        help='force use of hledger')
    parser.add_argument('--slow', action='store_true', default=False,
                        help='use slow, but possibly more robust, method of calling ledger (no subprocess)')
    args = parser.parse_args(args)
    if sys.argv[0][-16:] == "hledger-autosync":
      args.hledger = True

    if args.debug:
        logging.basicConfig(level=logging.DEBUG)
    if args.hledger:
        ledger = HLedger(args.ledger)
    elif args.slow:
        ledger = Ledger(ledger_file=args.ledger, no_pipe=True)
    else:
        ledger = mk_ledger(args.ledger)
    if args.PATH is None:
        config = OfxConfig()
        sync(ledger, config, max_days=args.max, resync=args.resync, indent=args.indent)
    else:
        import_ofx(ledger, args.PATH, args.account, indent=args.indent)

if __name__ == '__main__':
    run()

#!/usr/bin/env python

# Copyright (c) 2013, 2014 Erik Hetzner
# 
# This file is part of ledger-autosync
#
# ledger-autosync is free software: you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# ledger-autosync is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with ledger-autosync. If not, see
# <http://www.gnu.org/licenses/>.

from __future__ import absolute_import
import datetime
import time
from ofxclient.config import OfxConfig
from ofxparse import OfxParser
import argparse
from ofxclient.client import Client
from ledgerautosync import EmptyInstitutionException
from ledgerautosync.formatter import Formatter, AUTOSYNC_INITIAL, ALL_AUTOSYNC_INITIAL
from ledgerautosync.sync import Synchronizer
from ledgerautosync.ledgerwrap import mk_ledger, Ledger, HLedger
import logging
import re
import sys
import traceback
import os, os.path

def find_ledger_file():
    """Returns main ledger file path or raise exceptio if it cannot be found."""
    ledgerrcpath = os.path.abspath(os.path.expanduser("~/.ledgerrc"))
    if os.environ.has_key("LEDGER_FILE"):
        return os.path.abspath(os.path.expanduser(os.environ["LEDGER_FILE"]))
    elif os.path.exists(ledgerrcpath):
        # hacky
        ledgerrc = open(ledgerrcpath).read()
        return os.path.abspath(os.path.expanduser(re.match(r".*--file\s+([^\s]+).*", ledgerrc).group(1)))
    else:
        raise Exception("LEDGER_FILE environment variable not set, and no .ledgerrc file found, and -l argument no supplied.")

def maybe_print_initial(ofx, ledger, formatter):
    if (not(ledger.check_transaction_by_ofxid(formatter.mk_ofxid(AUTOSYNC_INITIAL))) and
        not(ledger.check_transaction_by_ofxid(ALL_AUTOSYNC_INITIAL))):
        print formatter.format_initial_balance(ofx.account.statement)

def sync(ledger, config, max_days=90, resync=False, indent=4, initial=False, assertions=False):
    sync = Synchronizer(ledger)
    for acct in config.accounts():
        try:
            (ofx, txns) = sync.get_new_txns(acct, resync=resync, max_days=max_days)
            formatter = Formatter(account=ofx.account, name=acct.description, ledger=ledger, indent=indent)
            if initial:
                maybe_print_initial(ofx, ledger, formatter)
            for txn in txns:
                print formatter.format_txn(txn)
            if assertions:
                print formatter.format_balance(ofx.account.statement)
        except KeyboardInterrupt:
            raise
        except:
            sys.stderr.write("Caught exception processing %s"%(acct.description))
            traceback.print_exc(file=sys.stderr)
                             
def import_ofx(ledger, path, accountname=None, indent=4, initial=False, assertions=False, fid=None):
    sync = Synchronizer(ledger)
    (ofx, txns) = sync.parse_file(path)
    if accountname is None:
        if ofx.account.institution is not None:
            accountname = "%s:%s"%(ofx.account.institution.organization, ofx.account.account_id)
        else:
            raise EmptyInstitutionException("Institution provided by OFX is empty and no accountname supplied!")
    formatter = Formatter(account=ofx.account, name=accountname, ledger=ledger, indent=indent, fid=fid)
    if initial:
        maybe_print_initial(ofx, ledger, formatter)
    for txn in txns:
        print formatter.format_txn(txn)
    if assertions:
        print formatter.format_balance(ofx.account.statement)
        
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
    parser.add_argument('--initial', action='store_true', default=False,
                        help='create initial balance entries')
    parser.add_argument('--fid', type=int, default=None,
                        help='pass in fid value for OFX files that do not supply it')
    parser.add_argument('--assertions', action='store_true', default=False,
                        help='create balance assertion entries')
    parser.add_argument('-d', '--debug', action='store_true', default=False,
                        help='enable debug logging')
    parser.add_argument('--hledger', action='store_true', default=False,
                        help='force use of hledger (on by default if invoked as hledger-autosync)')
    parser.add_argument('--slow', action='store_true', default=False,
                        help='use slow, but possibly more robust, method of calling ledger (no subprocess)')
    args = parser.parse_args(args)
    if sys.argv[0][-16:] == "hledger-autosync":
      args.hledger = True

    ledger_file = None
    if args.ledger:
        ledger_file = args.ledger
    else:
        ledger_file = find_ledger_file()
    if args.debug:
        logging.basicConfig(level=logging.DEBUG)
    if args.hledger:
        ledger = HLedger(ledger_file)
    elif args.slow:
        ledger = Ledger(ledger_file=ledger_file, no_pipe=True)
    else:
        ledger = mk_ledger(ledger_file)
    if args.PATH is None:
        config_dir = os.environ.get('XDG_CONFIG_HOME', os.path.join(os.path.expanduser("~"), '.config'))
        config_file = os.path.join(config_dir, 'ofxclient.ini')
        if (os.path.exists(config_file)):
            config = OfxConfig(file_name=config_file)
        else:
            config = OfxConfig()
        sync(ledger, config, max_days=args.max, resync=args.resync, indent=args.indent, initial=args.initial, assertions=args.assertions)
    else:
        import_ofx(ledger, args.PATH, args.account, indent=args.indent, initial=args.initial, assertions=args.assertions, fid=args.fid)

if __name__ == '__main__':
    run()

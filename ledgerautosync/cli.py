#!/usr/bin/env python

# Copyright (c) 2013, 2014 Erik Hetzner
# Portions Copyright (c) 2016 James S Blachly, MD
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
from ofxclient.config import OfxConfig
import argparse
import csv
from ledgerautosync import EmptyInstitutionException, LedgerAutosyncException
from ledgerautosync.converter import OfxConverter, CsvConverter, AUTOSYNC_INITIAL, \
    ALL_AUTOSYNC_INITIAL
from ledgerautosync.converter import SecurityList
from ledgerautosync.sync import OfxSynchronizer, CsvSynchronizer
from ledgerautosync.ledgerwrap import mk_ledger, Ledger, HLedger, LedgerPython
import logging
import re
import sys
import traceback
import os
import os.path
import imp


def find_ledger_file(ledgerrcpath=None):
    """Returns main ledger file path or raise exception if it cannot be \
found."""
    if ledgerrcpath is None:
        ledgerrcpath = os.path.abspath(os.path.expanduser("~/.ledgerrc"))
    if "LEDGER_FILE" in os.environ:
        return os.path.abspath(os.path.expanduser(os.environ["LEDGER_FILE"]))
    elif os.path.exists(ledgerrcpath):
        # hacky
        ledgerrc = open(ledgerrcpath)
        for line in ledgerrc.readlines():
            md = re.match(r"--file\s+([^\s]+).*", line)
            if md is not None:
                return os.path.abspath(os.path.expanduser(md.group(1)))
    else:
        return None


def print_results(converter, ofx, ledger, txns, args):
    """
    This function is the final common pathway of program:

    Print initial balance if requested;
    Print transactions surviving de-duplication filter;
    Print balance assertions if requested;
    Print commodity prices obtained from position statements
    """

    if args.initial:
        if (not(ledger.check_transaction_by_id
                ("ofxid", converter.mk_ofxid(AUTOSYNC_INITIAL))) and
                not(ledger.check_transaction_by_id("ofxid", ALL_AUTOSYNC_INITIAL))):
            print converter.format_initial_balance(ofx.account.statement)
    for txn in txns:
        print converter.convert(txn).format(args.indent)
    if args.assertions:
        print converter.format_balance(ofx.account.statement)

    # if OFX has positions use these to obtain commodity prices
    # and print "P" records to provide dated/timed valuations
    # Note that this outputs only the commodity price,
    # not your position (e.g. # shares), even though this is in the OFX record
    if hasattr(ofx.account.statement, 'positions'):
        for pos in ofx.account.statement.positions:
            print converter.format_position(pos)

def sync(ledger, accounts, args):
    sync = OfxSynchronizer(ledger)
    for acct in accounts:
        try:
            (ofx, txns) = sync.get_new_txns(acct, resync=args.resync,
                                            max_days=args.max)
            if ofx is not None:
                converter = OfxConverter(ofx=ofx,
                                         name=acct.description,
                                         ledger=ledger,
                                         indent=args.indent,
                                         unknownaccount=args.unknownaccount)
                print_results(converter, ofx, ledger, txns, args)
        except KeyboardInterrupt:
            raise
        except:
            sys.stderr.write("Caught exception processing %s" %
                             (acct.description))
            traceback.print_exc(file=sys.stderr)


def import_ofx(ledger, args):
    sync = OfxSynchronizer(ledger)
    (ofx, txns) = sync.parse_file(args.PATH)
    accountname = args.account
    if accountname is None:
        if ofx.account.institution is not None:
            accountname = "%s:%s" % (ofx.account.institution.organization,
                                     ofx.account.account_id)
        else:
            raise EmptyInstitutionException("Institution provided by OFX is \
empty and no accountname supplied!")

    converter = OfxConverter(ofx=ofx,
                             name=accountname,
                             ledger=ledger,
                             indent=args.indent,
                             fid=args.fid,
                             unknownaccount=args.unknownaccount)

    print_results(converter, ofx, ledger, txns, args)


def import_csv(ledger, args):
    if args.account is None:
        raise Exception("When importing a CSV file, you must specify an account name.")
    sync = CsvSynchronizer(ledger)
    accountname = args.account
    for txn in sync.parse_file(args.PATH, accountname=args.account):
        print txn.format(args.indent)

def load_plugins(config_dir):
    plugin_dir = os.path.join(config_dir, 'ledger-autosync', 'plugins')
    if os.path.isdir(plugin_dir):
        for plugin in filter(re.compile('.py$', re.IGNORECASE).search, os.listdir(plugin_dir)):
            # Quiet loader
            import ledgerautosync.plugins
            path = os.path.join(plugin_dir, plugin)
            imp.load_source('ledgerautosync.plugins.%s'%(os.path.splitext(plugin)[0]), path)

def run(args=None, config=None):
    if args is None:
        args = sys.argv[1:]

    parser = argparse.ArgumentParser(description='Synchronize ledger.')
    parser.add_argument('-m', '--max', type=int, default=90,
                        help='maximum number of days to process')
    parser.add_argument('-r', '--resync', action='store_true', default=False,
                        help='do not stop until max days reached')
    parser.add_argument('PATH', nargs='?', help='do not sync; import from OFX \
file')
    parser.add_argument('-a', '--account', type=str, default=None,
                        help='sync only the named account; \
if importing from file, set account name for import')
    parser.add_argument('-l', '--ledger', type=str, default=None,
                        help='specify ledger file to READ for syncing')
    parser.add_argument('-L', dest='no_ledger', action='store_true', default=False,
                        help='do not de-duplicate against a ledger file')
    parser.add_argument('-i', '--indent', type=int, default=4,
                        help='number of spaces to use for indentation')
    parser.add_argument('--initial', action='store_true', default=False,
                        help='create initial balance entries')
    parser.add_argument('--fid', type=int, default=None,
                        help='pass in fid value for OFX files that do not \
supply it')
    parser.add_argument('--unknown-account', type=str, dest='unknownaccount',
                        default=None,
                        help='specify account name to use when one can\'t be \
found by payee')
    parser.add_argument('--assertions', action='store_true', default=False,
                        help='create balance assertion entries')
    parser.add_argument('-d', '--debug', action='store_true', default=False,
                        help='enable debug logging')
    parser.add_argument('--hledger', action='store_true', default=False,
                        help='force use of hledger (on by default if invoked \
as hledger-autosync)')
    parser.add_argument('--python', action='store_true', default=False,
                        help='use the ledger python interface')
    parser.add_argument('--slow', action='store_true', default=False,
                        help='use slow, but possibly more robust, method of \
calling ledger (no subprocess)')
    parser.add_argument('--which', action='store_true', default=False,
                        help='display which version of ledger (cli), hledger, \
or ledger (python) will be used by ledger-autosync to check for previous \
transactions')
    args = parser.parse_args(args)
    if sys.argv[0][-16:] == "hledger-autosync":
        args.hledger = True

    ledger_file = None
    if args.ledger and args.no_ledger:
        raise LedgerAutosyncException('You cannot specify a ledger file and -L')
    elif args.ledger:
        ledger_file = args.ledger
    else:
        ledger_file = find_ledger_file()
    if args.debug:
        logging.basicConfig(level=logging.DEBUG)

    if ledger_file is None:
        sys.stderr.write("LEDGER_FILE environment variable not set, and no \
.ledgerrc file found, and -l argument was not supplied: running with deduplication disabled. \
All transactions will be printed!")
        ledger = None
    elif args.no_ledger:
        ledger = None
    elif args.hledger:
        ledger = HLedger(ledger_file)
    elif args.python:
        ledger = LedgerPython(ledger_file=ledger_file)
    elif args.slow:
        ledger = Ledger(ledger_file=ledger_file, no_pipe=True)
    else:
        ledger = mk_ledger(ledger_file)

    if args.which:
        sys.stderr.write("ledger-autosync is using ")
        if type(ledger) == Ledger:
            sys.stderr.write("ledger (cli)\n")
        elif type(ledger) == HLedger:
            sys.stderr.write("hledger\n")
        elif type(ledger) == LedgerPython:
            sys.stderr.write("ledger.so (python)\n")
        exit()

    config_dir = os.environ.get('XDG_CONFIG_HOME',
                                os.path.join(os.path.expanduser("~"),
                                             '.config'))

    load_plugins(config_dir)

    if args.PATH is None:
        if config is None:
            config_file = os.path.join(config_dir, 'ofxclient.ini')
            if (os.path.exists(config_file)):
                config = OfxConfig(file_name=config_file)
            else:
                config = OfxConfig()
        accounts = config.accounts()
        if args.account:
            accounts = [acct for acct in accounts
                        if acct.description == args.account]
        sync(ledger, accounts, args)
    else:
        _, file_extension = os.path.splitext(args.PATH)
        if file_extension == '.csv':
            import_csv(ledger, args)
        else:
            import_ofx(ledger, args)

if __name__ == '__main__':
    run()

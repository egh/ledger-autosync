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
from ledgerautosync import LedgerAutosyncException
from ledgerautosync.cli import run, find_ledger_file
from ledgerautosync.ledgerwrap import Ledger, LedgerPython, HLedger
from ofxclient.config import OfxConfig
import os.path
import tempfile
import sys
from StringIO import StringIO

from unittest import TestCase
from mock import Mock, call, patch
from nose.plugins.attrib import attr
from nose.tools import raises

class CliTest():
    def test_run(self):
        config = OfxConfig(os.path.join('fixtures', 'ofxclient.ini'))
        acct = config.accounts()[0]
        acct.download = Mock(side_effect=lambda *args, **kwargs:
                             file(os.path.join('fixtures', 'checking.ofx')))
        config.accounts = Mock(return_value=[acct])
        run(['-l', os.path.join('fixtures', 'empty.lgr')], config)
        acct.download.assert_has_calls([call(days=7), call(days=14)])
        self.assertEqual(config.accounts.call_count, 1)

    def test_run_csv_file(self):
        config = OfxConfig(os.path.join('fixtures', 'ofxclient.ini'))
        run(['-a', 'Paypal', '-l', os.path.join('fixtures', 'empty.lgr'), os.path.join('fixtures', 'paypal.csv')], config)

    def test_filter_account(self):
        config = OfxConfig(os.path.join('fixtures', 'ofxclient.ini'))
        foo = next(acct for acct in config.accounts()
                   if acct.description == 'Assets:Savings:Foo')
        bar = next(acct for acct in config.accounts()
                   if acct.description == 'Assets:Checking:Bar')
        foo.download = Mock(side_effect=lambda *args, **kwargs:
                            file(os.path.join('fixtures', 'checking.ofx')))
        bar.download = Mock()
        config.accounts = Mock(return_value=[foo, bar])
        run(['-l', os.path.join('fixtures', 'checking.lgr'),
             '-a', 'Assets:Savings:Foo'], config)
        foo.download.assert_has_calls([call(days=7)])
        bar.download.assert_not_called()

    def test_find_ledger_path(self):
        os.environ["LEDGER_FILE"] = "/tmp/foo"
        self.assertEqual(find_ledger_file(), "/tmp/foo", "Should use LEDGER_FILE to find ledger path.")

        (f, tmprcpath) = tempfile.mkstemp(".ledgerrc")
        os.close(f) # Who wants to deal with low-level file descriptors?
        with open(tmprcpath, 'w') as f:
            f.write("--bar foo\n")
            f.write("--file /tmp/bar\n")
            f.write("--foo bar\n")
        self.assertEqual(find_ledger_file(tmprcpath), "/tmp/foo", "Should prefer LEDGER_FILE to --file arg in ledgerrc")
        del os.environ["LEDGER_FILE"]
        self.assertEqual(find_ledger_file(tmprcpath), "/tmp/bar", "Should parse ledgerrc")
        os.unlink(tmprcpath)

    @raises(LedgerAutosyncException)
    def test_no_ledger_arg(self):
        config = OfxConfig(os.path.join('fixtures', 'ofxclient.ini'))
        run(['-l', os.path.join('fixtures', 'checking.lgr'),
             '-L'], config)

    def test_no_ledger(self):
        config = OfxConfig(os.path.join('fixtures', 'ofxclient.ini'))
        acct = config.accounts()[0]
        acct.download = Mock(side_effect=lambda *args, **kwargs:
                             file(os.path.join('fixtures', 'checking.ofx')))
        config.accounts = Mock(return_value=[acct])
        with patch('ledgerautosync.cli.find_ledger_file', return_value=None):
            with patch('sys.stderr', new_callable=StringIO) as mock_stdout:
                run([], config)
                self.assertEquals(mock_stdout.getvalue(), 'LEDGER_FILE environment variable not set, and no .ledgerrc file found, and -l argument was not supplied: running with deduplication disabled. All transactions will be printed!')

@attr('hledger')
class TestCliHledger(TestCase, CliTest):
    def setUp(self):
        self.empty_lgr = HLedger(os.path.join('fixtures', 'empty.lgr'))
        self.checking_lgr = HLedger(os.path.join('fixtures', 'checking.lgr'))


@attr('ledger')
class TestCliLedger(TestCase, CliTest):
    def setUp(self):
        self.empty_lgr = Ledger(os.path.join('fixtures', 'empty.lgr'),
                                no_pipe=True)
        self.checking_lgr = Ledger(os.path.join('fixtures', 'checking.lgr'),
                                   no_pipe=True)


@attr('ledger-python')
class TestCliLedgerPython(TestCase, CliTest):
    def setUp(self):
        self.empty_lgr = LedgerPython(os.path.join('fixtures', 'empty.lgr'))
        self.checking_lgr = LedgerPython(
            os.path.join('fixtures', 'checking.lgr'))

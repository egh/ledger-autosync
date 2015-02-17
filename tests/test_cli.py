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
from ledgerautosync.cli import sync, run
from ledgerautosync.ledgerwrap import Ledger, LedgerPython, HLedger
from ofxclient.config import OfxConfig
import os.path

from unittest import TestCase
from mock import Mock, PropertyMock
from nose.plugins.attrib import attr

class CliTest():
    def test_run(self):
        config = OfxConfig(os.path.join('fixtures', 'ofxclient.ini'))
        acct = config.accounts()[0]
        acct.download = Mock(return_value=file(os.path.join('fixtures', 'checking.ofx')))
        config.accounts = Mock(return_value=[acct])
        sync(self.empty_lgr, config.accounts(), 7)

    def test_empty_run(self):
        config = OfxConfig(os.path.join('fixtures', 'ofxclient.ini'))
        acct = config.accounts()[0]
        acct.download = Mock(return_value=file(os.path.join('fixtures', 'checking.ofx')))
        config.accounts = Mock(return_value=[acct])
        sync(self.checking_lgr, config.accounts(), 7)

    def test_filter_account(self):
        config = OfxConfig(os.path.join('fixtures', 'ofxclient.ini'))
        foo = next(acct for acct in config.accounts() if acct.description == 'Assets:Savings:Foo')
        bar = next(acct for acct in config.accounts() if acct.description == 'Assets:Checking:Bar')
        foo.download = Mock(return_value=file(os.path.join('fixtures', 'checking.ofx')))
        bar.download = PropertyMock(side_effect=Exception('Should not be called'))
        config.accounts = Mock(return_value=[foo, bar])
        run(['-l', os.path.join('fixtures', 'checking.lgr'),
             '-a', 'Assets:Savings:Foo'], config)

@attr('hledger')
class TestCliHledger(TestCase, CliTest):
    def setUp(self):
        self.empty_lgr = HLedger(os.path.join('fixtures', 'empty.lgr'))
        self.checking_lgr = HLedger(os.path.join('fixtures', 'checking.lgr'))


@attr('ledger')
class TestCliLedger(TestCase, CliTest):
    def setUp(self):
        self.empty_lgr = Ledger(os.path.join('fixtures', 'empty.lgr'), no_pipe=True)
        self.checking_lgr = Ledger(os.path.join('fixtures', 'checking.lgr'), no_pipe=True)


@attr('ledger-python')
class TestCliLedgerPython(TestCase, CliTest):
    def setUp(self):
        self.empty_lgr = LedgerPython(os.path.join('fixtures', 'empty.lgr'))
        self.checking_lgr = LedgerPython(os.path.join('fixtures', 'checking.lgr'))

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
from ledgerautosync.cli import sync
from ledgerautosync.ledgerwrap import Ledger, LedgerPython, HLedger
from ofxclient.config import OfxConfig
import os.path
import ledger

from unittest import TestCase
from mock import Mock

class TestCli(TestCase):
    def test_run(self):
        for lgr in [LedgerPython(os.path.join('fixtures', 'empty.lgr')),
                    HLedger(os.path.join('fixtures', 'empty.lgr')),
                    Ledger(os.path.join('fixtures', 'empty.lgr'), no_pipe=True)]:
            config = OfxConfig(os.path.join('fixtures', 'ofxclient.ini'))
            acct = config.accounts()[0]
            acct.download = Mock(return_value=file(os.path.join('fixtures', 'checking.ofx')))
            config.accounts = Mock(return_value=[acct])
            sync(lgr, config, 7)

    def test_empty_run(self):
        for lgr in [LedgerPython(os.path.join('fixtures', 'checking.lgr')),
                    HLedger(os.path.join('fixtures', 'checking.lgr')),
                    Ledger(os.path.join('fixtures', 'checking.lgr'), no_pipe=True)]:
            config = OfxConfig(os.path.join('fixtures', 'ofxclient.ini'))
            acct = config.accounts()[0]
            acct.download = Mock(return_value=file(os.path.join('fixtures', 'checking.ofx')))
            config.accounts = Mock(return_value=[acct])
            sync(lgr, config, 7)


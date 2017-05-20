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
import os
import os.path
from ofxparse import OfxParser
from ledgerautosync.ledgerwrap import Ledger
from ledgerautosync.sync import OfxSynchronizer, CsvSynchronizer

from unittest import TestCase
from nose.plugins.attrib import attr
from mock import Mock

@attr('generic')
class TestOfxSync(TestCase):
    def test_fresh_sync(self):
        ledger = Ledger(os.path.join('fixtures', 'empty.lgr'))
        sync = OfxSynchronizer(ledger)
        ofx = OfxParser.parse(file(os.path.join('fixtures', 'checking.ofx')))
        txns1 = ofx.account.statement.transactions
        txns2 = sync.filter(ofx)
        self.assertEqual(txns1, txns2)

    def test_sync_order(self):
        ledger = Ledger(os.path.join('fixtures', 'empty.lgr'))
        sync = OfxSynchronizer(ledger)
        ofx = OfxParser.parse(file(os.path.join('fixtures', 'checking_order.ofx')))
        txns = sync.filter(ofx)
        self.assertTrue(txns[0].date < txns[1].date and
                        txns[1].date < txns[2].date)

    def test_fully_synced(self):
        ledger = Ledger(os.path.join('fixtures', 'checking.lgr'))
        sync = OfxSynchronizer(ledger)
        (ofx, txns) = sync.parse_file(os.path.join('fixtures', 'checking.ofx'))
        self.assertEqual(txns, [])

    def test_partial_sync(self):
        ledger = Ledger(os.path.join('fixtures', 'checking-partial.lgr'))
        sync = OfxSynchronizer(ledger)
        (ofx, txns) = sync.parse_file(os.path.join('fixtures', 'checking.ofx'))
        self.assertEqual(len(txns), 1)

    def test_no_new_txns(self):
        ledger = Ledger(os.path.join('fixtures', 'checking.lgr'))
        acct = Mock()
        acct.download = Mock(return_value=file(os.path.join('fixtures', 'checking.ofx')))
        sync = OfxSynchronizer(ledger)
        self.assertEqual(len(sync.get_new_txns(acct, 7, 7)[1]), 0)

    def test_all_new_txns(self):
        ledger = Ledger(os.path.join('fixtures', 'empty.lgr'))
        acct = Mock()
        acct.download = Mock(return_value=file(os.path.join('fixtures', 'checking.ofx')))
        sync = OfxSynchronizer(ledger)
        self.assertEqual(len(sync.get_new_txns(acct, 7, 7)[1]), 3)

    def test_comment_txns(self):
        ledger = Ledger(os.path.join('fixtures', 'empty.lgr'))
        sync = OfxSynchronizer(ledger)
        (ofx, txns) = sync.parse_file(os.path.join('fixtures', 'comments.ofx'))
        self.assertEqual(len(txns), 1)

    def test_sync_no_ledger(self):
        acct = Mock()
        acct.download = Mock(return_value=file(os.path.join('fixtures', 'checking.ofx')))
        sync = OfxSynchronizer(None)
        self.assertEqual(len(sync.get_new_txns(acct, 7, 7)[1]), 3)

@attr('generic')
class TestCsvSync(TestCase):
    def test_fresh_sync(self):
        ledger = Ledger(os.path.join('fixtures', 'empty.lgr'))
        sync = CsvSynchronizer(ledger)
        self.assertEqual(
            2, len(sync.parse_file(
                os.path.join('fixtures', 'paypal.csv'))))

    def test_partial_sync(self):
        ledger = Ledger(os.path.join('fixtures', 'paypal.lgr'))
        sync = CsvSynchronizer(ledger)
        self.assertEqual(
            1, len(sync.parse_file(
                os.path.join('fixtures', 'paypal.csv'))))

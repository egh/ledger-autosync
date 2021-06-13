# Copyright (c) 2013-2021 Erik Hetzner
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


import os
import os.path
from unittest.mock import Mock

from ofxparse import OfxParser

from ledgerautosync.ledgerwrap import Ledger
from ledgerautosync.sync import CsvSynchronizer, OfxSynchronizer


def test_fresh_sync():
    ledger = Ledger(os.path.join("fixtures", "empty.lgr"))
    sync = OfxSynchronizer(ledger)
    with open(os.path.join("fixtures", "checking.ofx"), "rb") as ofx_file:
        ofx = OfxParser.parse(ofx_file)
        txns1 = ofx.account.statement.transactions
        txns2 = sync.filter(txns1, ofx.account.account_id)
        assert txns1 == txns2


def test_sync_order():
    ledger = Ledger(os.path.join("fixtures", "empty.lgr"))
    sync = OfxSynchronizer(ledger)
    with open(os.path.join("fixtures", "checking_order.ofx"), "rb") as ofx_file:
        ofx = OfxParser.parse(ofx_file)
        txns = sync.filter(ofx.account.statement.transactions, ofx.account.account_id)
        assert txns[0].date < txns[1].date
        assert txns[1].date < txns[2].date


def test_fully_synced():
    ledger = Ledger(os.path.join("fixtures", "checking.lgr"))
    sync = OfxSynchronizer(ledger)
    ofx = OfxSynchronizer.parse_file(os.path.join("fixtures", "checking.ofx"))
    txns = sync.filter(ofx.account.statement.transactions, ofx.account.account_id)
    assert txns == []


def test_partial_sync():
    ledger = Ledger(os.path.join("fixtures", "checking-partial.lgr"))
    sync = OfxSynchronizer(ledger)
    ofx = OfxSynchronizer.parse_file(os.path.join("fixtures", "checking.ofx"))
    txns = sync.filter(ofx.account.statement.transactions, ofx.account.account_id)
    assert len(txns) == 1


def test_no_new_txns():
    ledger = Ledger(os.path.join("fixtures", "checking.lgr"))
    acct = Mock()
    acct.download = Mock(
        return_value=open(os.path.join("fixtures", "checking.ofx"), "rb")
    )
    sync = OfxSynchronizer(ledger)
    assert len(sync.get_new_txns(acct, 7, 7)[1]) == 0


def test_all_new_txns():
    ledger = Ledger(os.path.join("fixtures", "empty.lgr"))
    acct = Mock()
    acct.download = Mock(
        return_value=open(os.path.join("fixtures", "checking.ofx"), "rb")
    )
    sync = OfxSynchronizer(ledger)
    assert len(sync.get_new_txns(acct, 7, 7)[1]) == 3


def test_comment_txns():
    ledger = Ledger(os.path.join("fixtures", "empty.lgr"))
    sync = OfxSynchronizer(ledger)
    ofx = OfxSynchronizer.parse_file(os.path.join("fixtures", "comments.ofx"))
    txns = sync.filter(ofx.account.statement.transactions, ofx.account.account_id)
    assert len(txns) == 1


def test_sync_no_ledger():
    acct = Mock()
    acct.download = Mock(
        return_value=open(os.path.join("fixtures", "checking.ofx"), "rb")
    )
    sync = OfxSynchronizer(None)
    assert len(sync.get_new_txns(acct, 7, 7)[1]) == 3


def test_paypal_fresh_sync():
    ledger = Ledger(os.path.join("fixtures", "empty.lgr"))
    sync = CsvSynchronizer(ledger)
    assert 2 == len(sync.parse_file(os.path.join("fixtures", "paypal.csv")))


def test_sync_paypal_no_ledger():
    sync = CsvSynchronizer(None)
    assert 2 == len(sync.parse_file(os.path.join("fixtures", "paypal.csv")))


def test_paypal_partial_sync():
    ledger = Ledger(os.path.join("fixtures", "paypal.lgr"))
    sync = CsvSynchronizer(ledger)
    assert 1 == len(sync.parse_file(os.path.join("fixtures", "paypal.csv")))

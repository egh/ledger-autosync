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
from ledgerautosync.ledgerwrap import Ledger, HLedger, LedgerPython
from nose.plugins.attrib import attr
from unittest import TestCase
import os
import os.path


class LedgerTest(object):
    ledger_path = os.path.join('fixtures', 'checking.lgr')
    dynamic_ledger_path = os.path.join('fixtures', 'checking-dynamic-account.lgr')

    def check_transaction(self):
        self.assertTrue(self.lgr.check_transaction_by_id("ofxid", "1101.1452687~7.0000486"))

    def test_nonexistent_transaction(self):
        self.assertFalse(self.lgr.check_transaction_by_id("ofxid", "FOO"))

    def test_empty_transaction(self):
        self.assertTrue(self.lgr.check_transaction_by_id("ofxid", "empty"))

    def test_get_account_by_payee(self):
        account = self.lgr.get_account_by_payee("AUTOMATIC WITHDRAWAL, ELECTRIC BILL WEB(S )", exclude="Assets:Foo")
        self.assertEqual(account, "Expenses:Bar")

    def test_get_ambiguous_account_by_payee(self):
        account = self.dynamic_lgr.get_account_by_payee("Generic", exclude="Assets:Foo")
        # shoud use the latest
        self.assertEqual(account, "Expenses:Bar")

    def test_ofx_quoting(self):
        self.assertEqual(self.lgr.check_transaction_by_id("ofxid", "1/2"), True,
                         msg="Did not find 1/2 in %s" % (self.lgr))


@attr('hledger')
class TestHledger(TestCase, LedgerTest):
    def setUp(self):
        self.lgr = HLedger(self.ledger_path)
        self.dynamic_lgr = HLedger(self.dynamic_ledger_path)


@attr('ledger')
class TestLedger(LedgerTest, TestCase):
    def setUp(self):
        self.lgr = Ledger(self.ledger_path, no_pipe=True)
        self.dynamic_lgr = Ledger(self.dynamic_ledger_path, no_pipe=True)


@attr('ledger-python')
class TestLedgerPython(TestCase, LedgerTest):
    def setUp(self):
        self.lgr = LedgerPython(self.ledger_path)
        self.dynamic_lgr = LedgerPython(self.dynamic_ledger_path)

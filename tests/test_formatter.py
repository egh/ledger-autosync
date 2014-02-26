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
from ledgerautosync.formatter import Formatter
from ledgerautosync.ledgerwrap import Ledger
import os.path

from ofxparse import OfxParser

from unittest import TestCase
from mock import Mock

class TestFormatter(TestCase):
    def test_checking(self):
        ofx = OfxParser.parse(file(os.path.join('fixtures', 'checking.ofx')))
        formatter = Formatter(account=ofx.account, name="Foo", indent=2)
        self.assertEqual(formatter.format_txn(ofx.account.statement.transactions[0]),
"""2011/03/31 DIVIDEND EARNED FOR PERIOD OF 03/01/2011 THROUGH 03/31/2011 ANNUAL PERCENTAGE YIELD EARNED IS 0.05%
  ; ofxid: 1101.1452687~7.0000486
  Foo                                          $0.01
  Expenses:Misc                               -$0.01
""")
        self.assertEqual(formatter.format_txn(ofx.account.statement.transactions[1]),
"""2011/04/05 AUTOMATIC WITHDRAWAL, ELECTRIC BILL WEB(S )
  ; ofxid: 1101.1452687~7.0000487
  Foo                                        -$34.51
  Expenses:Misc                               $34.51
""")
        self.assertEqual(formatter.format_txn(ofx.account.statement.transactions[2]),
"""2011/04/07 RETURNED CHECK FEE, CHECK # 319 FOR $45.33 ON 04/07/11
  ; ofxid: 1101.1452687~7.0000488
  Foo                                        -$25.00
  Expenses:Misc                               $25.00
""")

    def test_indent(self):
        ofx = OfxParser.parse(file(os.path.join('fixtures', 'checking.ofx')))
        formatter = Formatter(account=ofx.account, name="Foo", indent=4)
        self.assertEqual(formatter.format_txn(ofx.account.statement.transactions[0]),
"""2011/03/31 DIVIDEND EARNED FOR PERIOD OF 03/01/2011 THROUGH 03/31/2011 ANNUAL PERCENTAGE YIELD EARNED IS 0.05%
    ; ofxid: 1101.1452687~7.0000486
    Foo                                        $0.01
    Expenses:Misc                             -$0.01
""")

    def test_investments(self):
        ofx = OfxParser.parse(file(os.path.join('fixtures', 'fidelity.ofx')))
        formatter = Formatter(account=ofx.account, name="Foo", indent=2)
        self.assertEqual(formatter.format_txn(ofx.account.statement.transactions[0]),
"""2012/07/20 YOU BOUGHT
  ; ofxid: 7776.01234567890.0123456789020201120120720
  Foo                                      100.00000 458140100 @ $25.635000000
  Foo                                      -$2563.50
""")

    def test_dynamic_account(self):
        ofx = OfxParser.parse(file(os.path.join('fixtures', 'checking.ofx')))
        ledger = Ledger(os.path.join('fixtures', 'checking-dynamic-account.lgr'))
        formatter = Formatter(account=ofx.account, name="Assets:Foo", ledger=ledger, indent=2)
        self.assertEqual(formatter.format_txn(ofx.account.statement.transactions[1]),
"""2011/04/05 AUTOMATIC WITHDRAWAL, ELECTRIC BILL WEB(S )
  ; ofxid: 1101.1452687~7.0000487
  Assets:Foo                                 -$34.51
  Expenses:Bar                                $34.51
""")

    def test_balance_assertion(self):
        ofx = OfxParser.parse(file(os.path.join('fixtures', 'checking.ofx')))
        ledger = Ledger(os.path.join('fixtures', 'checking.lgr'))
        formatter = Formatter(account=ofx.account, name="Assets:Foo", ledger=ledger)
        self.assertEqual(formatter.format_balance(ofx.account.statement),
"""2013/05/25 * --Autosync Balance Assertion
    Assets:Foo                                 $0.00 = $100.99
""")

    def test_initial_balance(self):
        ofx = OfxParser.parse(file(os.path.join('fixtures', 'checking.ofx')))
        ledger = Ledger(os.path.join('fixtures', 'checking.lgr'))
        formatter = Formatter(account=ofx.account, name="Assets:Foo", ledger=ledger)
        self.assertEqual(formatter.format_initial_balance(ofx.account.statement),
"""2000/01/01 * --Autosync Initial Balance
    ; ofxid: 1101.1452687~7.autosync_initial
    Assets:Foo                               $160.49
    Assets:Equity                           -$160.49
""")
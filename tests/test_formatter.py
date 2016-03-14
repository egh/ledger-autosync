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
from decimal import Decimal

from ofxparse import OfxParser

from nose.plugins.attrib import attr
from tests import LedgerTestCase


@attr('generic')
class TestFormatter(LedgerTestCase):
    def test_checking(self):
        ofx = OfxParser.parse(file(os.path.join('fixtures', 'checking.ofx')))
        formatter = Formatter(account=ofx.account, name="Foo")
        self.assertEqualLedgerPosting(formatter.format_txn(ofx.account.statement.transactions[0]),
"""2011/03/31 DIVIDEND EARNED FOR PERIOD OF 03/01/2011 THROUGH 03/31/2011 ANNUAL PERCENTAGE YIELD EARNED IS 0.05%
  ; ofxid: 1101.1452687~7.0000486
  Foo  $0.01
  Expenses:Misc  -$0.01
""")
        self.assertEqualLedgerPosting(formatter.format_txn(ofx.account.statement.transactions[1]),
"""2011/04/05 AUTOMATIC WITHDRAWAL, ELECTRIC BILL WEB(S )
  ; ofxid: 1101.1452687~7.0000487
  Foo  -$34.51
  Expenses:Misc  $34.51
""")

        self.assertEqualLedgerPosting(formatter.format_txn(ofx.account.statement.transactions[2]),
"""2011/04/07 RETURNED CHECK FEE, CHECK # 319 FOR $45.33 ON 04/07/11
  ; ofxid: 1101.1452687~7.0000488
  Foo  -$25.00
  Expenses:Misc  $25.00
""")

    def test_indent(self):
        ofx = OfxParser.parse(file(os.path.join('fixtures', 'checking.ofx')))
        formatter = Formatter(account=ofx.account, name="Foo", indent=4)
        # testing indent, so do not use the string collapsing version of assert
        self.assertEqual(formatter.format_txn(ofx.account.statement.transactions[0]),
"""2011/03/31 DIVIDEND EARNED FOR PERIOD OF 03/01/2011 THROUGH 03/31/2011 ANNUAL PERCENTAGE YIELD EARNED IS 0.05%
    ; ofxid: 1101.1452687~7.0000486
    Foo                                        $0.01
    Expenses:Misc                             -$0.01
""")

    def test_investments(self):
        ofx = OfxParser.parse(file(os.path.join('fixtures', 'fidelity.ofx')))
        formatter = Formatter(account=ofx.account, name="Foo")
        self.assertEqualLedgerPosting(formatter.format_txn(ofx.account.statement.transactions[0]),
"""2012/07/20 YOU BOUGHT
  ; ofxid: 7776.01234567890.0123456789020201120120720
  Foo  100.00000 "458140100" @ $25.635000000
  Assets:Unknown  -$2563.50
""")
        # test no payee/memo
        self.assertEqualLedgerPosting(formatter.format_txn(ofx.account.statement.transactions[1]),
"""2012/07/27 UNKNOWN
  ; ofxid: 7776.01234567890.0123456789020901120120727
  Foo  128.00000 "G7945E105" @ $39.390900000
  Assets:Unknown  -$5042.04
""")

    def test_dynamic_account(self):
        ofx = OfxParser.parse(file(os.path.join('fixtures', 'checking.ofx')))
        ledger = Ledger(os.path.join('fixtures', 'checking-dynamic-account.lgr'))
        formatter = Formatter(account=ofx.account, name="Assets:Foo", ledger=ledger)
        self.assertEqualLedgerPosting(formatter.format_txn(ofx.account.statement.transactions[1]),
"""2011/04/05 AUTOMATIC WITHDRAWAL, ELECTRIC BILL WEB(S )
  ; ofxid: 1101.1452687~7.0000487
  Assets:Foo  -$34.51
  Expenses:Bar  $34.51
""")

    def test_balance_assertion(self):
        ofx = OfxParser.parse(file(os.path.join('fixtures', 'checking.ofx')))
        ledger = Ledger(os.path.join('fixtures', 'checking.lgr'))
        formatter = Formatter(account=ofx.account, name="Assets:Foo", ledger=ledger)
        self.assertEqualLedgerPosting(formatter.format_balance(ofx.account.statement),
"""2013/05/25 * --Autosync Balance Assertion
  Assets:Foo  $0.00 = $100.99
""")

    def test_initial_balance(self):
        ofx = OfxParser.parse(file(os.path.join('fixtures', 'checking.ofx')))
        ledger = Ledger(os.path.join('fixtures', 'checking.lgr'))
        formatter = Formatter(account=ofx.account, name="Assets:Foo", ledger=ledger)
        self.assertEqualLedgerPosting(formatter.format_initial_balance(ofx.account.statement),
"""2000/01/01 * --Autosync Initial Balance
  ; ofxid: 1101.1452687~7.autosync_initial
  Assets:Foo  $160.49
  Assets:Equity  -$160.49
""")

    def test_unknownaccount(self):
        ofx = OfxParser.parse(file(os.path.join('fixtures', 'checking.ofx')))
        formatter = Formatter(account=ofx.account, name="Foo",
                              unknownaccount='Expenses:Unknown')
        self.assertEqualLedgerPosting(formatter.format_txn(ofx.account.statement.transactions[0]),
"""2011/03/31 DIVIDEND EARNED FOR PERIOD OF 03/01/2011 THROUGH 03/31/2011 ANNUAL PERCENTAGE YIELD EARNED IS 0.05%
  ; ofxid: 1101.1452687~7.0000486
  Foo  $0.01
  Expenses:Unknown  -$0.01
""")

    def test_quote_commodity(self):
        ofx = OfxParser.parse(file(os.path.join('fixtures', 'fidelity.ofx')))
        formatter = Formatter(account=ofx.account, name="Foo")
        self.assertEqualLedgerPosting(formatter.format_txn(ofx.account.statement.transactions[0]),
"""2012/07/20 YOU BOUGHT
  ; ofxid: 7776.01234567890.0123456789020201120120720
  Foo  100.00000 "458140100" @ $25.635000000
  Assets:Unknown  -$2563.50
""")

    # Check that <TRANSFER> txns are parsed.
    def test_transfer_txn(self):
        ofx = OfxParser.parse(file(os.path.join('fixtures', 'investment_401k.ofx')))
        formatter = Formatter(account=ofx.account, name="Foo",
                              unknownaccount='Expenses:Unknown')
        if len(ofx.account.statement.transactions) > 2:
            # older versions of ofxparse would skip these transactions
            self.assertEqualLedgerPosting(formatter.format_txn(ofx.account.statement.transactions[2]),
"""2014/06/30 UNKNOWN
    ; ofxid: 1234.12345678.123456-01.3
    Foo  -9.060702 BAZ @ $21.928764
    Foo  $198.69
""")

    def test_format_amount(self):
        ofx = OfxParser.parse(file(os.path.join('fixtures', 'fidelity.ofx')))
        formatter = Formatter(account=ofx.account, name="Foo", indent=4,
                              unknownaccount='Expenses:Unknown')
        self.assertEqual("$10.00",
                         formatter.format_amount(Decimal("10.001")),
                         "Formats to 2 points precision, $ by default")
        self.assertEqual("10.00 USD",
                         formatter.format_amount(Decimal(10), currency="USD"),
                         "Longer commodity names come after")
        self.assertEqual("-$10.00",
                         formatter.format_amount(Decimal(10), reverse=True),
                         "Reverse flag works.")
        self.assertEqual("10.00 \"ABC123\"",
                         formatter.format_amount(Decimal(10), currency="ABC123"),
                         "Currencies with numbers are quoted")
        self.assertEqual("10.00 \"A BC\"",
                         formatter.format_amount(Decimal(10), currency="A BC"),
                         "Currencies with whitespace are quoted")
        self.assertEqual("$10.001",
                         formatter.format_amount(Decimal("10.001"),
                                                 unlimited=True))

    def test_position(self):
        ofx = OfxParser.parse(file(os.path.join('fixtures', 'investment_401k.ofx')))
        formatter = Formatter(account=ofx.account, name="Foo", indent=4,
                              unknownaccount='Expenses:Unknown')
        self.assertEqual(formatter.format_position(ofx.account.statement.positions[0]),
                         """P 2014/06/30 06:00:00 FOO 22.517211
""")

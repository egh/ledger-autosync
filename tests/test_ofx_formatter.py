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
from ledgerautosync.converter import OfxConverter
from ledgerautosync.ledgerwrap import Ledger
import os.path
from decimal import Decimal

from ofxparse import OfxParser

from nose.plugins.attrib import attr
from tests import LedgerTestCase


@attr('generic')
class TestOfxConverter(LedgerTestCase):
    def test_checking(self):
        ofx = OfxParser.parse(file(os.path.join('fixtures', 'checking.ofx')))
        converter = OfxConverter(ofx=ofx, name="Foo")
        self.assertEqualLedgerPosting(converter.convert(ofx.account.statement.transactions[0]).format(),
"""2011/03/31 DIVIDEND EARNED FOR PERIOD OF 03/01/2011 THROUGH 03/31/2011 ANNUAL PERCENTAGE YIELD EARNED IS 0.05%
  ; ofxid: 1101.1452687~7.0000486
  Foo  $0.01
  Expenses:Misc  -$0.01
""")
        self.assertEqualLedgerPosting(converter.convert(ofx.account.statement.transactions[1]).format(),
"""2011/04/05 AUTOMATIC WITHDRAWAL, ELECTRIC BILL WEB(S )
  ; ofxid: 1101.1452687~7.0000487
  Foo  -$34.51
  Expenses:Misc  $34.51
""")

        self.assertEqualLedgerPosting(converter.convert(ofx.account.statement.transactions[2]).format(),
"""2011/04/07 RETURNED CHECK FEE, CHECK # 319 FOR $45.33 ON 04/07/11
  ; ofxid: 1101.1452687~7.0000488
  Foo  -$25.00
  Expenses:Misc  $25.00
""")

    def test_indent(self):
        ofx = OfxParser.parse(file(os.path.join('fixtures', 'checking.ofx')))
        converter = OfxConverter(ofx=ofx, name="Foo", indent=4)
        # testing indent, so do not use the string collapsing version of assert
        self.assertEqual(converter.convert(ofx.account.statement.transactions[0]).format(),
"""2011/03/31 DIVIDEND EARNED FOR PERIOD OF 03/01/2011 THROUGH 03/31/2011 ANNUAL PERCENTAGE YIELD EARNED IS 0.05%
    ; ofxid: 1101.1452687~7.0000486
    Foo                                                     $0.01
    Expenses:Misc                                          -$0.01
""")

    def test_investments(self):
        ofx = OfxParser.parse(file(os.path.join('fixtures', 'fidelity.ofx')))
        converter = OfxConverter(ofx=ofx, name="Foo")
        self.assertEqualLedgerPosting(converter.convert(ofx.account.statement.transactions[0]).format(),
"""2012/07/20 YOU BOUGHT
  ; ofxid: 7776.01234567890.0123456789020201120120720
  Foo  100.00000 INTC @ $25.635000000
  Assets:Unknown  -$2563.50
""")
        # test no payee/memo
        self.assertEqualLedgerPosting(converter.convert(ofx.account.statement.transactions[1]).format(),
"""2012/07/27 Foo: buystock
  ; ofxid: 7776.01234567890.0123456789020901120120727
  Foo  128.00000 SDRL @ $39.390900000
  Assets:Unknown  -$5042.04
""")

    def test_dynamic_account(self):
        ofx = OfxParser.parse(file(os.path.join('fixtures', 'checking.ofx')))
        ledger = Ledger(os.path.join('fixtures', 'checking-dynamic-account.lgr'))
        converter = OfxConverter(ofx=ofx, name="Assets:Foo", ledger=ledger)
        self.assertEqualLedgerPosting(converter.convert(ofx.account.statement.transactions[1]).format(),
"""2011/04/05 AUTOMATIC WITHDRAWAL, ELECTRIC BILL WEB(S )
  ; ofxid: 1101.1452687~7.0000487
  Assets:Foo  -$34.51
  Expenses:Bar  $34.51
""")

    def test_balance_assertion(self):
        ofx = OfxParser.parse(file(os.path.join('fixtures', 'checking.ofx')))
        ledger = Ledger(os.path.join('fixtures', 'checking.lgr'))
        converter = OfxConverter(ofx=ofx, name="Assets:Foo", ledger=ledger)
        self.assertEqualLedgerPosting(converter.format_balance(ofx.account.statement),
"""2013/05/25 * --Autosync Balance Assertion
  Assets:Foo  $0.00 = $100.99
""")

    def test_initial_balance(self):
        ofx = OfxParser.parse(file(os.path.join('fixtures', 'checking.ofx')))
        ledger = Ledger(os.path.join('fixtures', 'checking.lgr'))
        converter = OfxConverter(ofx=ofx, name="Assets:Foo", ledger=ledger)
        self.assertEqualLedgerPosting(converter.format_initial_balance(ofx.account.statement),
"""2000/01/01 * --Autosync Initial Balance
  ; ofxid: 1101.1452687~7.autosync_initial
  Assets:Foo  $160.49
  Assets:Equity  -$160.49
""")

    def test_unknownaccount(self):
        ofx = OfxParser.parse(file(os.path.join('fixtures', 'checking.ofx')))
        converter = OfxConverter(ofx=ofx, name="Foo",
                                 unknownaccount='Expenses:Unknown')
        self.assertEqualLedgerPosting(converter.convert(ofx.account.statement.transactions[0]).format(),
"""2011/03/31 DIVIDEND EARNED FOR PERIOD OF 03/01/2011 THROUGH 03/31/2011 ANNUAL PERCENTAGE YIELD EARNED IS 0.05%
  ; ofxid: 1101.1452687~7.0000486
  Foo  $0.01
  Expenses:Unknown  -$0.01
""")

    def test_quote_commodity(self):
        ofx = OfxParser.parse(file(os.path.join('fixtures', 'fidelity.ofx')))
        converter = OfxConverter(ofx=ofx, name="Foo")
        self.assertEqualLedgerPosting(converter.convert(ofx.account.statement.transactions[0]).format(),
"""2012/07/20 YOU BOUGHT
  ; ofxid: 7776.01234567890.0123456789020201120120720
  Foo  100.00000 INTC @ $25.635000000
  Assets:Unknown  -$2563.50
""")

    # Check that <TRANSFER> txns are parsed.
    def test_transfer_txn(self):
        ofx = OfxParser.parse(file(os.path.join('fixtures', 'investment_401k.ofx')))
        converter = OfxConverter(ofx=ofx, name="Foo",
                                 unknownaccount='Expenses:Unknown')
        if len(ofx.account.statement.transactions) > 2:
            # older versions of ofxparse would skip these transactions
            if hasattr(ofx.account.statement.transactions[2], 'tferaction'):
                # unmerged pull request
                self.assertEqualLedgerPosting(converter.convert(ofx.account.statement.transactions[2]).format(),
"""2014/06/30 Foo: transfer: out
    ; ofxid: 1234.12345678.123456-01.3
    Foo  -9.060702 BAZ @ $21.928764
    Transfer  $198.69
""")
            else:
                            self.assertEqualLedgerPosting(converter.convert(ofx.account.statement.transactions[2]).format(),
"""2014/06/30 Foo: transfer
    ; ofxid: 1234.12345678.123456-01.3
    Foo  -9.060702 BAZ @ $21.928764
    Transfer  $198.69
""")


    def test_position(self):
        ofx = OfxParser.parse(file(os.path.join('fixtures', 'cusip.ofx')))
        converter = OfxConverter(ofx=ofx, name="Foo", indent=4,
                                 unknownaccount='Expenses:Unknown')
        self.assertEqual(converter.format_position(ofx.account.statement.positions[0]),
                         """P 2016/10/08 07:30:08 SHSAX 47.8600000
""")

    def test_dividend(self):
        ofx = OfxParser.parse(file(os.path.join('fixtures', 'income.ofx')))
        converter = OfxConverter(ofx=ofx, name="Foo")
        self.assertEqualLedgerPosting(converter.convert(ofx.account.statement.transactions[0]).format(),
"""2016/10/12 DIVIDEND RECEIVED
    ; dividend_from: cusip_redacted
    ; ofxid: 1234.12345678.123456-01.redacted
    Foo                                     $1234.56
    Income:Dividends                       -$1234.56
""")

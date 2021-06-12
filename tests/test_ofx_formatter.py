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

# flake8: noqa E501

import os.path

from nose.plugins.attrib import attr
from ofxparse import OfxParser

from ledgerautosync.converter import OfxConverter, SecurityList
from ledgerautosync.ledgerwrap import Ledger
from tests import LedgerTestCase


@attr("generic")
class TestOfxConverter(LedgerTestCase):
    def test_checking(self):
        with open(os.path.join("fixtures", "checking.ofx"), "rb") as ofx_file:
            ofx = OfxParser.parse(ofx_file)
        converter = OfxConverter(account=ofx.account, name="Foo")
        self.assertEqualLedgerPosting(
            converter.convert(ofx.account.statement.transactions[0]).format(),
            """2011/03/31 DIVIDEND EARNED FOR PERIOD OF 03/01/2011 THROUGH 03/31/2011 ANNUAL PERCENTAGE YIELD EARNED IS 0.05%
  Foo  $0.01
  ; ofxid: 1101.1452687~7.0000486
  Expenses:Misc  -$0.01
""",
        )
        self.assertEqualLedgerPosting(
            converter.convert(ofx.account.statement.transactions[1]).format(),
            """2011/04/05 AUTOMATIC WITHDRAWAL, ELECTRIC BILL WEB(S )
  Foo  -$34.51
  ; ofxid: 1101.1452687~7.0000487
  Expenses:Misc  $34.51
""",
        )

        self.assertEqualLedgerPosting(
            converter.convert(ofx.account.statement.transactions[2]).format(),
            """2011/04/07 (319) RETURNED CHECK FEE, CHECK # 319 FOR $45.33 ON 04/07/11
  Foo  -$25.00
  ; ofxid: 1101.1452687~7.0000488
  Expenses:Misc  $25.00
""",
        )

    def test_indent(self):
        with open(os.path.join("fixtures", "checking.ofx"), "rb") as ofx_file:
            ofx = OfxParser.parse(ofx_file)
        converter = OfxConverter(account=ofx.account, name="Foo", indent=4)
        # testing indent, so do not use the string collapsing version of assert
        self.assertEqual(
            converter.convert(ofx.account.statement.transactions[0]).format(),
            """2011/03/31 DIVIDEND EARNED FOR PERIOD OF 03/01/2011 THROUGH 03/31/2011 ANNUAL PERCENTAGE YIELD EARNED IS 0.05%
    Foo                                                     $0.01
    ; ofxid: 1101.1452687~7.0000486
    Expenses:Misc                                          -$0.01
""",
        )

    def test_shortenaccount(self):
        with open(os.path.join("fixtures", "checking.ofx"), "rb") as ofx_file:
            ofx = OfxParser.parse(ofx_file)
        converter = OfxConverter(
            account=ofx.account, name="Foo", indent=4, shortenaccount=True
        )
        # testing indent, so do not use the string collapsing version of assert
        self.assertEqual(
            converter.convert(ofx.account.statement.transactions[0]).format(),
            """2011/03/31 DIVIDEND EARNED FOR PERIOD OF 03/01/2011 THROUGH 03/31/2011 ANNUAL PERCENTAGE YIELD EARNED IS 0.05%
    Foo                                                     $0.01
    ; ofxid: 1101.87~7.0000486
    Expenses:Misc                                          -$0.01
""",
        )

    def test_hardcodeaccount(self):
        with open(os.path.join("fixtures", "checking.ofx"), "rb") as ofx_file:
            ofx = OfxParser.parse(ofx_file)
        converter = OfxConverter(
            account=ofx.account, name="Foo", indent=4, hardcodeaccount="9999"
        )
        # testing indent, so do not use the string collapsing version of assert
        self.assertEqual(
            converter.convert(ofx.account.statement.transactions[0]).format(),
            """2011/03/31 DIVIDEND EARNED FOR PERIOD OF 03/01/2011 THROUGH 03/31/2011 ANNUAL PERCENTAGE YIELD EARNED IS 0.05%
    Foo                                                     $0.01
    ; ofxid: 1101.9999.0000486
    Expenses:Misc                                          -$0.01
""",
        )

    def test_investments(self):
        with open(os.path.join("fixtures", "fidelity.ofx"), "rb") as ofx_file:
            ofx = OfxParser.parse(ofx_file)
        converter = OfxConverter(
            account=ofx.account, name="Foo", security_list=SecurityList(ofx)
        )
        self.assertEqualLedgerPosting(
            converter.convert(ofx.account.statement.transactions[0]).format(),
            """2012/07/20 YOU BOUGHT
  Foo  100.00000 INTC @ $25.635000000
  ; ofxid: 7776.01234567890.0123456789020201120120720
  Assets:Unknown  -$2563.50
  Expenses:Commission  $7.95
""",
        )
        # test no payee/memo
        self.assertEqualLedgerPosting(
            converter.convert(ofx.account.statement.transactions[1]).format(),
            """2012/07/27 Foo: buystock
  Foo  128.00000 SDRL @ $39.390900000
  ; ofxid: 7776.01234567890.0123456789020901120120727
  Assets:Unknown  -$5042.04
  Expenses:Commission  $7.95
""",
        )

    def test_fee(self):
        """Test that fees are parsed correctly.

        In this case we have a 7-cent fee. We need to make sure that
        the net sale price which shows up is the gross price of 3239.44
        minus 7 cents which equals 3239.37 and that the 7 cent fee
        shows up as an extra posting.
        """
        with open(os.path.join("fixtures", "fidelity_fee.ofx"), "rb") as ofx_file:
            ofx = OfxParser.parse(ofx_file)
        converter = OfxConverter(
            account=ofx.account, name="Foo", security_list=SecurityList(ofx)
        )
        # test fee
        self.assertEqualLedgerPosting(
            converter.convert(ofx.account.statement.transactions[1]).format(),
            """2012/08/01 SELL
    Foo                                        -100.0 "929042109" @ $32.3944
    ; ofxid: 7776.01234567890.0123456789021401420120801
    Assets:Unknown                                       $3239.37
    Expenses:Fees                                           $0.07
""",
        )
        # test fee and comission
        self.assertEqualLedgerPosting(
            converter.convert(ofx.account.statement.transactions[0]).format(),
            """2020/05/22=2020/05/26 SELL
  Foo  -1.0 "Z9977810Z" @ $8.27
  ; ofxid: 7776.01234567890.987654321
  Assets:Unknown  $8.25
  Expenses:Fees  $0.02
  Expenses:Commission  $1.00
""",
        )

    def test_dynamic_account(self):
        with open(os.path.join("fixtures", "checking.ofx"), "rb") as ofx_file:
            ofx = OfxParser.parse(ofx_file)
        ledger = Ledger(os.path.join("fixtures", "checking-dynamic-account.lgr"))
        converter = OfxConverter(account=ofx.account, name="Assets:Foo", ledger=ledger)
        self.assertEqualLedgerPosting(
            converter.convert(ofx.account.statement.transactions[1]).format(),
            """2011/04/05 AUTOMATIC WITHDRAWAL, ELECTRIC BILL WEB(S )
  Assets:Foo  -$34.51
  ; ofxid: 1101.1452687~7.0000487
  Expenses:Bar  $34.51
""",
        )

    def test_balance_assertion(self):
        with open(os.path.join("fixtures", "checking.ofx"), "rb") as ofx_file:
            ofx = OfxParser.parse(ofx_file)
        ledger = Ledger(os.path.join("fixtures", "checking.lgr"))
        converter = OfxConverter(account=ofx.account, name="Assets:Foo", ledger=ledger)
        self.assertEqualLedgerPosting(
            converter.format_balance(ofx.account.statement),
            """2013/05/25 * --Autosync Balance Assertion
  Assets:Foo  $0.00 = $100.99
""",
        )

    def test_initial_balance(self):
        with open(os.path.join("fixtures", "checking.ofx"), "rb") as ofx_file:
            ofx = OfxParser.parse(ofx_file)
        ledger = Ledger(os.path.join("fixtures", "checking.lgr"))
        converter = OfxConverter(account=ofx.account, name="Assets:Foo", ledger=ledger)
        self.assertEqualLedgerPosting(
            converter.format_initial_balance(ofx.account.statement),
            """2000/01/01 * --Autosync Initial Balance
  Assets:Foo  $160.49
  ; ofxid: 1101.1452687~7.autosync_initial
  Assets:Equity  -$160.49
""",
        )

    def test_unknownaccount(self):
        with open(os.path.join("fixtures", "checking.ofx"), "rb") as ofx_file:
            ofx = OfxParser.parse(ofx_file)
        converter = OfxConverter(
            account=ofx.account, name="Foo", unknownaccount="Expenses:Unknown"
        )
        self.assertEqualLedgerPosting(
            converter.convert(ofx.account.statement.transactions[0]).format(),
            """2011/03/31 DIVIDEND EARNED FOR PERIOD OF 03/01/2011 THROUGH 03/31/2011 ANNUAL PERCENTAGE YIELD EARNED IS 0.05%
  Foo  $0.01
  ; ofxid: 1101.1452687~7.0000486
  Expenses:Unknown  -$0.01
""",
        )

    def test_quote_commodity(self):
        with open(os.path.join("fixtures", "fidelity.ofx"), "rb") as ofx_file:
            ofx = OfxParser.parse(ofx_file)
        converter = OfxConverter(
            account=ofx.account, name="Foo", security_list=SecurityList(ofx)
        )
        self.assertEqualLedgerPosting(
            converter.convert(ofx.account.statement.transactions[0]).format(),
            """2012/07/20 YOU BOUGHT
  Foo  100.00000 INTC @ $25.635000000
  ; ofxid: 7776.01234567890.0123456789020201120120720
  Assets:Unknown  -$2563.50
  Expenses:Commission  $7.95
""",
        )

    # Check that <TRANSFER> txns are parsed.
    def test_transfer_txn(self):
        with open(os.path.join("fixtures", "investment_401k.ofx"), "rb") as ofx_file:
            ofx = OfxParser.parse(ofx_file)
        converter = OfxConverter(
            account=ofx.account, name="Foo", unknownaccount="Expenses:Unknown"
        )
        if len(ofx.account.statement.transactions) > 2:
            # older versions of ofxparse would skip these transactions
            if hasattr(ofx.account.statement.transactions[2], "tferaction"):
                # unmerged pull request
                self.assertEqualLedgerPosting(
                    converter.convert(ofx.account.statement.transactions[2]).format(),
                    """2014/06/30 Foo: transfer: out
    Foo  -9.060702 BAZ @ $21.928764
    ; ofxid: 1234.12345678.123456-01.3
    Transfer  $198.69
""",
                )
            else:
                self.assertEqualLedgerPosting(
                    converter.convert(ofx.account.statement.transactions[2]).format(),
                    """2014/06/30 Foo: transfer
    Foo  -9.060702 BAZ @ $21.928764
    ; ofxid: 1234.12345678.123456-01.3
    Transfer  $198.69
""",
                )

    def test_position(self):
        with open(os.path.join("fixtures", "cusip.ofx"), "rb") as ofx_file:
            ofx = OfxParser.parse(ofx_file)
        converter = OfxConverter(
            account=ofx.account,
            name="Foo",
            indent=4,
            unknownaccount="Expenses:Unknown",
            security_list=SecurityList(ofx),
        )
        self.assertEqual(
            converter.format_position(ofx.account.statement.positions[0]),
            """P 2016/10/08 07:30:08 SHSAX 47.8600000
""",
        )

    def test_dividend(self):
        with open(os.path.join("fixtures", "income.ofx"), "rb") as ofx_file:
            ofx = OfxParser.parse(ofx_file)
        converter = OfxConverter(account=ofx.account, name="Foo")
        self.assertEqualLedgerPosting(
            converter.convert(ofx.account.statement.transactions[0]).format(),
            """2016/10/12 DIVIDEND RECEIVED
    ; dividend_from: cusip_redacted
    Foo                                     $1234.56
    ; ofxid: 1234.12345678.123456-01.redacted
    Income:Dividends                       -$1234.56
""",
        )

    def test_checking_custom_payee(self):
        with open(os.path.join("fixtures", "checking.ofx"), "rb") as ofx_file:
            ofx = OfxParser.parse(ofx_file)
        converter = OfxConverter(account=ofx.account, name="Foo", payee_format="{memo}")
        self.assertEqual(
            converter.format_payee(ofx.account.statement.transactions[0]),
            "DIVIDEND EARNED FOR PERIOD OF 03/01/2011 THROUGH 03/31/2011 ANNUAL PERCENTAGE YIELD EARNED IS 0.05%",
        )
        converter = OfxConverter(
            account=ofx.account, name="Foo", payee_format="{payee}"
        )
        self.assertEqual(
            converter.format_payee(ofx.account.statement.transactions[0]),
            "DIVIDEND EARNED FOR PERIOD OF 03",
        )
        converter = OfxConverter(
            account=ofx.account, name="Foo", payee_format="{account}"
        )
        self.assertEqual(
            converter.format_payee(ofx.account.statement.transactions[0]), "Foo"
        )
        converter = OfxConverter(
            account=ofx.account, name="Foo", payee_format=" {account} "
        )
        self.assertEqual(
            converter.format_payee(ofx.account.statement.transactions[0]), "Foo"
        )

    def test_investments_custom_payee(self):
        with open(os.path.join("fixtures", "investment_401k.ofx"), "rb") as ofx_file:
            ofx = OfxParser.parse(ofx_file)
        converter = OfxConverter(
            account=ofx.account, name="Foo", payee_format="{txntype}"
        )
        self.assertEqual(
            converter.format_payee(ofx.account.statement.transactions[1]), "transfer"
        )
        converter = OfxConverter(
            account=ofx.account, name="Foo", payee_format="{tferaction}"
        )
        self.assertEqual(
            converter.format_payee(ofx.account.statement.transactions[1]), "in"
        )

    def test_payee_match(self):
        with open(
            os.path.join("fixtures", "checking-payee-match.ofx"), "rb"
        ) as ofx_file:
            ofx = OfxParser.parse(ofx_file)
        ledger = Ledger(os.path.join("fixtures", "checking.lgr"))
        converter = OfxConverter(account=ofx.account, name="Foo", ledger=ledger)
        self.assertEqualLedgerPosting(
            converter.convert(ofx.account.statement.transactions[0]).format(),
            """2011/03/31 Match Payee
  Foo  -$0.01
  ; ofxid: 1101.1452687~7.0000489
  Expenses:Bar  $0.01
""",
        )

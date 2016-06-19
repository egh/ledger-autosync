# Copyright (c) 2013-2016 Erik Hetzner
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
from ledgerautosync.converter import Converter, CsvConverter, AmazonConverter, PaypalConverter, Amount, Posting
from decimal import Decimal
import csv

from nose.plugins.attrib import attr
from tests import LedgerTestCase


@attr('generic')
class TestPosting(LedgerTestCase):
    def test_format(self):
        self.assertRegexpMatches(
            Posting(
                "Foo",
                Amount(Decimal("10.00"), "$")
            ).format(indent=2),
            r'^  Foo.*$')


@attr('generic')
class TestAmount(LedgerTestCase):
    def test_amount(self):
        self.assertEqual(
            "$10.00",
            Amount(Decimal("10.001"), "$").format(),
            "Formats to 2 points precision by default")
        self.assertEqual(
            "10.00 USD",
            Amount(Decimal(10), "USD").format(),
            "Longer commodity names come after")
        self.assertEqual(
            "-$10.00",
            Amount(Decimal(10), "$", reverse=True).format(),
            "Reverse flag works.")
        self.assertEqual(
            "10.00 \"ABC123\"",
            Amount(Decimal(10), "ABC123").format(),
            "Currencies with numbers are quoted")
        self.assertEqual(
            "10.00 \"A BC\"",
            Amount(Decimal(10), "A BC").format(),
            "Currencies with whitespace are quoted")
        self.assertEqual(
            "$10.001",
            Amount(Decimal("10.001"), "$", unlimited=True).format())

@attr('generic')
class TestPaypalConverter(LedgerTestCase):
    def test_format(self):
        with open('fixtures/paypal.csv', 'rb') as f:
            dialect = csv.Sniffer().sniff(f.read(1024))
            f.seek(0)
            dialect.skipinitialspace = True
            reader = csv.DictReader(f, dialect=dialect)
            converter = CsvConverter.make_converter(name='Foo', csv=reader)
            self.assertEqual(type(converter), PaypalConverter)
            self.assertEqual(
                converter.format_txn(reader.next()),
                """2016/06/04 Jane Doe someone@example.net My Friend ID: XYZ1, Recurring Payment Sent
    ; csvid: paypal.XYZ1
    Foo                                   -20.00 USD
    Expenses:Misc                          20.00 USD
""")
            self.assertEqual(
                converter.format_txn(reader.next()),
                """2016/06/04 Debit Card ID: XYZ2, Charge From Debit Card
    ; csvid: paypal.XYZ2
    Foo                                    20.00 USD
    Transfer:Paypal                       -20.00 USD
""")

@attr('generic')
class TestAmazonConverter(LedgerTestCase):
    def test_format(self):
        with open('fixtures/amazon.csv', 'rb') as f:
            dialect = csv.Sniffer().sniff(f.read(1024))
            f.seek(0)
            dialect.skipinitialspace = True
            reader = csv.DictReader(f, dialect=dialect)
            converter = CsvConverter.make_converter(name='Foo', csv=reader)
            self.assertEqual(type(converter), AmazonConverter)
            self.assertEqual(
                converter.format_txn(reader.next()),
                """2016/01/29 Best Soap Ever
    ; url: https://www.amazon.com/gp/css/summary/print.html/ref=od_aui_print_invoice?ie=UTF8&orderID=123-4567890-1234567
    ; csvid: amazon.123-4567890-1234567
    Foo                                       $21.90
    Expenses:Misc                            -$21.90
""")

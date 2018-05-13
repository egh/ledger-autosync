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


from ledgerautosync.converter import Converter, CsvConverter, AmazonConverter, MintConverter, PaypalConverter, PaypalAlternateConverter, Amount, Posting
from decimal import Decimal
import hashlib
import csv

from nose.plugins.attrib import attr
from tests import LedgerTestCase


@attr('generic')
class TestPosting(LedgerTestCase):
    def test_format(self):
        self.assertEqualLedgerPosting(
            Posting(
                "Foo",
                Amount(Decimal("10.00"), "$"),
                metadata={'foo': 'bar'}
            ).format(indent=2),
            "  Foo  $10.00\n  ; foo: bar\n")

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
class TestCsvConverter(LedgerTestCase):
    def test_get_csv_id(self):
        converter = CsvConverter(None)
        h = {'foo': 'bar', 'bar': 'foo'}
        self.assertEqual(converter.get_csv_id(h),
                         hashlib.md5("bar=foo\nfoo=bar\n").hexdigest())

class CsvConverterTestCase(LedgerTestCase):
    def make_converter(self, f, name=None):
        dialect = csv.Sniffer().sniff(f.read(1024))
        f.seek(0)
        dialect.skipinitialspace = True
        reader = csv.DictReader(f, dialect=dialect)
        converter = CsvConverter.make_converter(set(reader.fieldnames), dialect, name)
        f.seek(0)
        reader = csv.DictReader(f, dialect=dialect)
        return (reader, converter)

@attr('generic')
class TestPaypalConverter(CsvConverterTestCase):
    def test_format(self):
        with open('fixtures/paypal.csv') as f:
            (reader, converter) = self.make_converter(f, 'Foo')
            self.assertEqual(type(converter), PaypalConverter)
            self.assertEqual(
                converter.convert(next(reader)).format(),
                """2016/06/04 Jane Doe someone@example.net My Friend ID: XYZ1, Recurring Payment Sent
    Foo                                                -20.00 USD
    ; csvid: paypal.XYZ1
    Expenses:Misc                                       20.00 USD
""")
            self.assertEqual(
                converter.convert(next(reader)).format(),
                """2016/06/04 Debit Card ID: XYZ2, Charge From Debit Card
    Foo                                               1120.00 USD
    ; csvid: paypal.XYZ2
    Transfer:Paypal                                  -1120.00 USD
""")

@attr('generic')
class TestPaypalAlternateConverter(CsvConverterTestCase):
    def test_format(self):
        with open('fixtures/paypal_alternate.csv') as f:
            (reader, converter) = self.make_converter(f, 'Foo')
            self.assertEqual(type(converter), PaypalAlternateConverter)
            self.assertEqual(
                converter.convert(next(reader)).format(),
                """2016/12/31 Some User: Payment Sent
    Foo                                                   -$12.34
    ; csvid: 1209a7bb0d17276248d463b71a6a8b8c
    Expenses:Misc                                          $12.34
""")
            self.assertEqual(
                converter.convert(next(reader)).format(),
                """2016/12/31 Bank Account: Add Funds from a Bank Account
    Foo                                                    $12.34
    ; csvid: 581e62da71bab74c7ce61854c2b6b6a5
    Transfer:Paypal                                       -$12.34
""")

    def test_mk_amount(self):
        converter = PaypalAlternateConverter(None)
        row = { "Currency": "USD", "Amount": "12.34" }
        self.assertEqual(converter.mk_amount(row), Amount(Decimal('12.34'), "USD"))

@attr('generic')
class TestAmazonConverter(CsvConverterTestCase):
    def test_format(self):
        with open('fixtures/amazon.csv') as f:
            (reader, converter) = self.make_converter(f, 'Foo')
            self.assertEqual(type(converter), AmazonConverter)
            self.assertEqual(
                converter.convert(next(reader)).format(),
                """2016/01/29 Best Soap Ever
    Foo                                                    $21.90
    ; url: https://www.amazon.com/gp/css/summary/print.html/ref=od_aui_print_invoice?ie=UTF8&orderID=123-4567890-1234567
    ; csvid: amazon.123-4567890-1234567
    Expenses:Misc                                         -$21.90
""")

@attr('generic')
class TestAmazonConverter2(CsvConverterTestCase):
    def test_format(self):
        with open('fixtures/amazon2.csv') as f:
            (reader, converter) = self.make_converter(f, 'Foo')
            self.assertEqual(type(converter), AmazonConverter)
            self.assertEqual(
                converter.convert(next(reader)).format(),
                """2017/06/05 Test " double quote
    Foo                                                     $9.99
    ; url: https://www.amazon.com/gp/css/summary/print.html/ref=od_aui_print_invoice?ie=UTF8&orderID=111-1111111-1111111
    ; csvid: amazon.111-1111111-1111111
    Expenses:Misc                                          -$9.99
""")

@attr('generic')
class TestMintConverter(CsvConverterTestCase):
    def test_format(self):
        with open('fixtures/mint.csv') as f:
            (reader, converter) = self.make_converter(f)
            self.assertEqual(type(converter), MintConverter)
            self.assertEqual(
                converter.convert(next(reader)).format(),
                """2016/08/02 Amazon
    1234                                                   $29.99
    ; csvid: mint.a7c028a73d76956453dab634e8e5bdc1
    Expenses:Shopping                                     -$29.99
""")
            self.assertEqual(
                converter.convert(next(reader)).format(),
                """2016/06/02 Autopay Rautopay Auto
    1234                                                 -$123.45
    ; csvid: mint.a404e70594502dd62bfc6f15d80b7cd7
    Credit Card Payment                                   $123.45
""")

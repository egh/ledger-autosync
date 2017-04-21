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
from ledgerautosync.converter import Converter, CsvConverter, AmazonConverter, MintConverter, PaypalConverter, Amount, Posting
from decimal import Decimal
import hashlib
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
class TestCsvConverter(LedgerTestCase):
    def test_get_csv_id(self):
        converter = CsvConverter(None)
        h = {'foo': 'bar', 'bar': 'foo'}
        self.assertEqual(converter.get_csv_id(h),
                         hashlib.md5("bar=foo\nfoo=bar\n").hexdigest())


@attr('generic')
class TestPaypalConverter(LedgerTestCase):
    def test_format(self):
        with open('fixtures/paypal.csv', 'rb') as f:
            dialect = csv.Sniffer().sniff(f.read(1024))
            f.seek(0)
            dialect.skipinitialspace = True
            reader = csv.DictReader(f, dialect=dialect)
            converter = CsvConverter.make_converter(reader, name='Foo')
            self.assertEqual(type(converter), PaypalConverter)
            self.assertEqual(
                converter.convert(reader.next()).format(),
                """2016/06/04 Jane Doe someone@example.net My Friend ID: XYZ1, Recurring Payment Sent
    ; csvid: paypal.XYZ1
    Foo                                                -20.00 USD
    Expenses:Misc                                       20.00 USD
""")
            self.assertEqual(
                converter.convert(reader.next()).format(),
                """2016/06/04 Debit Card ID: XYZ2, Charge From Debit Card
    ; csvid: paypal.XYZ2
    Foo                                                 20.00 USD
    Transfer:Paypal                                    -20.00 USD
""")

@attr('generic')
class TestAmazonConverter(LedgerTestCase):
    def test_format(self):
        with open('fixtures/amazon.csv', 'rb') as f:
            dialect = csv.Sniffer().sniff(f.read(1024))
            f.seek(0)
            dialect.skipinitialspace = True
            reader = csv.DictReader(f, dialect=dialect)
            converter = CsvConverter.make_converter(reader, name='Foo')
            self.assertEqual(type(converter), AmazonConverter)
            self.assertEqual(
                converter.convert(reader.next()).format(),
                """2016/01/29 Best Soap Ever
    ; url: https://www.amazon.com/gp/css/summary/print.html/ref=od_aui_print_invoice?ie=UTF8&orderID=123-4567890-1234567
    ; csvid: amazon.123-4567890-1234567
    Foo                                                    $21.90
    Expenses:Misc                                         -$21.90
""")

@attr('generic')
class TestMintConverter(LedgerTestCase):
    def test_format(self):
        with open('fixtures/mint.csv', 'rb') as f:
            dialect = csv.Sniffer().sniff(f.read(1024))
            f.seek(0)
            dialect.skipinitialspace = True
            reader = csv.DictReader(f, dialect=dialect)
            converter = CsvConverter.make_converter(reader)
            self.assertEqual(type(converter), MintConverter)
            self.assertEqual(
                converter.convert(reader.next()).format(),
                """2016/08/02 Amazon
    ; csvid: mint.a7c028a73d76956453dab634e8e5bdc1
    1234                                                   $29.99
    Expenses:Shopping                                     -$29.99
""")
            self.assertEqual(
                converter.convert(reader.next()).format(),
                """2016/06/02 Autopay Rautopay Auto
    ; csvid: mint.a404e70594502dd62bfc6f15d80b7cd7
    1234                                                 -$123.45
    Credit Card Payment                                   $123.45
""")

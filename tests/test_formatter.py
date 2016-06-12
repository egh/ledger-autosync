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
from ledgerautosync.formatter import Formatter, CsvFormatter
from decimal import Decimal
import csv

from nose.plugins.attrib import attr
from tests import LedgerTestCase


@attr('generic')
class TestFormatter(LedgerTestCase):
    def test_format_amount(self):
        formatter = Formatter()
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
                         formatter.format_amount(Decimal(10),
                                                 currency="ABC123"),
                         "Currencies with numbers are quoted")
        self.assertEqual("10.00 \"A BC\"",
                         formatter.format_amount(Decimal(10), currency="A BC"),
                         "Currencies with whitespace are quoted")
        self.assertEqual("$10.001",
                         formatter.format_amount(Decimal("10.001"),
                                                 unlimited=True))
        eur_formatter = Formatter(currency="EUR")
        self.assertEqual("10.00 EUR",
                         eur_formatter.format_amount(Decimal("10.00")),
                         "Uses default currency")

        indent_formatter = Formatter(indent=2)
        self.assertRegexpMatches(
            indent_formatter.format_txn_line(
                "Foo",
                indent_formatter.format_amount(Decimal("10.00"))),
            r'^  Foo.*$')


@attr('generic')
class TestCsvFormatter(LedgerTestCase):
    def test_format_amount(self):
        with open('fixtures/paypal.csv', 'rb') as f:
            dialect = csv.Sniffer().sniff(f.read(1024))
            f.seek(0)
            dialect.skipinitialspace = True
            reader = csv.DictReader(f, dialect=dialect)
            formatter = CsvFormatter(name='Foo', csv=reader)
            self.assertEqual(formatter.csv_type, 'paypal')
            self.assertEqual(
                formatter.format_txn(reader.next()),
                """2016/06/04 Jane Doe someone@example.net My Friend ID: XYZ1, Recurring Payment Sent
    ; csvid: paypal.XYZ1
    Foo                                   -20.00 USD
    Transfer:Paypal                        20.00 USD
""")
            self.assertEqual(
                formatter.format_txn(reader.next()),
                """2016/06/04 Debit Card ID: XYZ2, Charge From Debit Card
    ; csvid: paypal.XYZ2
    Foo                                    20.00 USD
    Transfer:Paypal                       -20.00 USD
""")

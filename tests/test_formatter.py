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
from ledgerautosync.formatter import Formatter
from decimal import Decimal

from nose.plugins.attrib import attr
from tests import LedgerTestCase


@attr('generic')
class TestOfxFormatter(LedgerTestCase):
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
        eur_formatter = Formatter("EUR")
        self.assertEqual("10.00 EUR",
                         eur_formatter.format_amount(Decimal("10.00")),
                         "Uses default currency")

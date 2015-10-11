# Copyright (c) 2013-2015 Erik Hetzner
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

from unittest import TestCase
import re


class LedgerTestCase(TestCase):
    def assertEqualLedgerPosting(self, a, b, msg=None):
        """Checks that two strings are the same posting. Collapses all space
        sequences > len(2)."""
        a1 = re.sub('  +', '  ', a)
        b1 = re.sub('  +', '  ', b)
        return self.assertEqual(a1, b1, msg=msg)

# Copyright (c) 2013-2021 Erik Hetzner
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


import os

import pytest
from ofxparse import OfxParser

from ledgerautosync.ledgerwrap import HLedger, Ledger, LedgerPython

LEDGER = [HLedger, Ledger, LedgerPython]


@pytest.fixture(params=LEDGER)
def ledger(request):
    lgr_name = request.node.get_closest_marker("lgr_file").args[0]
    ledger_impls = request.node.get_closest_marker("ledger_impls")
    kwargs = {}
    if request.param == Ledger:
        kwargs["no_pipe"] = True
    if not request.param.available():
        pytest.skip(f"{request.param} not found")
    if ledger_impls is not None:
        if request.param not in ledger_impls.args[0]:
            pytest.skip("Test not applicable for this ledger.")
    return request.param(os.path.join("fixtures", lgr_name), **kwargs)


@pytest.fixture
def ofx(request):
    ofx_name = request.node.get_closest_marker("ofx_file").args[0]
    with open(os.path.join("fixtures", ofx_name), "rb") as ofx_file:
        yield OfxParser.parse(ofx_file)

# -*- coding: utf-8 -*-
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


import os.path

import pytest
from ofxclient.config import OfxConfig

from ledgerautosync import EmptyInstitutionException
from ledgerautosync.cli import run
from ledgerautosync.converter import OfxConverter
from ledgerautosync.sync import OfxSynchronizer


@pytest.fixture
def ofx_sync(ledger):
    return OfxSynchronizer(ledger)


@pytest.mark.lgr_file("empty.lgr")
def test_no_institution_no_fid(ledger):
    with pytest.raises(EmptyInstitutionException):
        config = OfxConfig(os.path.join("fixtures", "ofxclient.ini"))
        run(
            [
                os.path.join("fixtures", "no-institution.ofx"),
                "-l",
                os.path.join("fixtures", "empty.lgr"),
                "-a",
                "Assets:Savings:Foo",
            ],
            config,
        )


@pytest.mark.ofx_file("no-institution.ofx")
@pytest.mark.lgr_file("empty.lgr")
def test_no_institution(ofx, ofx_sync):
    txns = ofx_sync.filter(ofx.account.statement.transactions, ofx.account.account_id)
    assert len(txns) == 3


@pytest.mark.ofx_file("no-institution.ofx")
@pytest.mark.lgr_file("empty.lgr")
def test_no_institution_no_accountname(ofx):
    with pytest.raises(EmptyInstitutionException):
        OfxConverter(account=ofx.account, name=None)


@pytest.mark.ofx_file("apostrophe.ofx")
@pytest.mark.lgr_file("empty.lgr")
def test_apostrophe(ofx, ofx_sync):
    txns = ofx_sync.filter(ofx.account.statement.transactions, ofx.account.account_id)
    assert len(txns) == 1


@pytest.mark.ofx_file("fidelity-one-dtsettle.ofx")
@pytest.mark.lgr_file("empty.lgr")
def test_one_settleDate(ofx, ofx_sync):
    txns = ofx_sync.filter(ofx.account.statement.transactions, ofx.account.account_id)
    assert len(txns) == 17


@pytest.mark.ofx_file("accented_characters_latin1.ofx")
@pytest.mark.lgr_file("empty.lgr")
def test_accented_characters_latin1(ofx, ofx_sync):
    txns = ofx_sync.filter(ofx.account.statement.transactions, ofx.account.account_id)
    converter = OfxConverter(account=ofx.account, name="Foo")
    assert converter.format_payee(txns[0]) == "Virement Interac à: Jean"
    assert len(txns) == 1

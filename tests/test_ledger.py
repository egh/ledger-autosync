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
import os.path
import tempfile

import pytest

from ledgerautosync.ledgerwrap import Ledger, LedgerPython


@pytest.mark.lgr_file("checking.lgr")
def test_check_transaction(ledger):
    assert ledger.check_transaction_by_id("ofxid", "1101.1452687~7.0000486")


@pytest.mark.lgr_file("checking.lgr")
def test_nonexistent_transaction(ledger):
    assert not ledger.check_transaction_by_id("ofxid", "FOO")


@pytest.mark.lgr_file("checking.lgr")
def test_empty_transaction(ledger):
    assert ledger.check_transaction_by_id("ofxid", "empty")


@pytest.mark.lgr_file("checking.lgr")
def test_get_account_by_payee(ledger):
    account = ledger.get_account_by_payee(
        "AUTOMATIC WITHDRAWAL, ELECTRIC BILL WEB(S )", exclude="Assets:Foo"
    )
    assert account == "Expenses:Bar"


@pytest.mark.lgr_file("checking-dynamic-account.lgr")
def test_get_ambiguous_account_by_payee(ledger):
    account = ledger.get_account_by_payee("Generic", exclude="Assets:Foo")
    # shoud use the latest
    assert account == "Expenses:Bar"


@pytest.mark.lgr_file("checking.lgr")
def test_ofx_payee_quoting(ledger):
    payees = [
        "PAYEE TEST/SLASH",
        "PAYEE TEST,COMMA",
        "PAYEE TEST:COLON",
        "PAYEE TEST*STAR",
        "PAYEE TEST#HASH",
        "PAYEE TEST.PERIOD",
    ]
    for payee in payees:
        assert (
            ledger.get_account_by_payee(payee, ["Assets:Foo"]) is not None
        ), "Did not find %s in %s" % (payee, ledger)


# TODO Broken on current hledger
@pytest.mark.lgr_file("checking.lgr")
@pytest.mark.ledger_impls([Ledger, LedgerPython])
def test_ofx_payee_quote_quote(ledger):
    payees = [
        'PAYEE TEST"QUOTE',
    ]
    for payee in payees:
        assert (
            ledger.get_account_by_payee(payee, ["Assets:Foo"]) is not None
        ), "Did not find %s in %s" % (payee, ledger)


@pytest.mark.lgr_file("checking.lgr")
def test_ofx_id_quoting(ledger):
    assert (
        ledger.check_transaction_by_id("ofxid", "1/2") is True
    ), "Did not find 1/2 in %s" % (ledger)


@pytest.mark.lgr_file("checking.lgr")
def test_load_payees(ledger):
    ledger.load_payees()
    assert ledger.payees["PAYEE TEST:COLON"] == ["Assets:Foo", "Income:Bar"]


@pytest.mark.lgr_file("empty.lgr")
def test_load_payees_with_empty_ledger(ledger):
    ledger.load_payees()


# class TestLedger(LedgerTest, TestCase):
#     def setUp(ledger):
#         self.empty_lgr = Ledger(os.path.join("fixtures", "empty.lgr"), no_pipe=True)
#         ledger = Ledger(self.ledger_path, no_pipe=True)
#         self.dynamic_lgr = Ledger(self.dynamic_ledger_path, no_pipe=True)


@pytest.mark.lgr_file("checking.lgr")
@pytest.mark.ledger_impls([Ledger, LedgerPython])
def test_args_only(ledger):
    (f, tmprcpath) = tempfile.mkstemp(".ledgerrc")
    os.close(f)  # Who wants to deal with low-level file descriptors?
    # Create an init file that will narrow the test data to a period that
    # contains no trasnactions
    with open(tmprcpath, "w") as f:
        f.write("--period 2012")
    # If the command returns no trasnactions, as we would expect if we
    # parsed the init file, then this will throw an exception.
    next(ledger.run([""]))
    os.unlink(tmprcpath)

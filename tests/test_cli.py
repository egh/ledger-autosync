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
import re
import tempfile
from io import StringIO
from unittest.mock import Mock, call, patch

import pytest
from ofxclient.config import OfxConfig

from ledgerautosync import LedgerAutosyncException
from ledgerautosync.cli import find_ledger_file, run


def test_run():
    config = OfxConfig(os.path.join("fixtures", "ofxclient.ini"))
    acct = config.accounts()[0]
    acct.download = Mock(
        side_effect=lambda *args, **kwargs: open(
            os.path.join("fixtures", "checking.ofx"), "rb"
        )
    )
    config.accounts = Mock(return_value=[acct])
    run(["-l", os.path.join("fixtures", "empty.lgr")], config)
    acct.download.assert_has_calls([call(days=7), call(days=14)])
    assert config.accounts.call_count == 1


def test_run_csv_file():
    config = OfxConfig(os.path.join("fixtures", "ofxclient.ini"))
    run(
        [
            "-a",
            "Paypal",
            "-l",
            os.path.join("fixtures", "empty.lgr"),
            os.path.join("fixtures", "paypal.csv"),
        ],
        config,
    )


def test_filter_account():
    config = OfxConfig(os.path.join("fixtures", "ofxclient.ini"))
    foo = next(
        acct for acct in config.accounts() if acct.description == "Assets:Savings:Foo"
    )
    bar = next(
        acct for acct in config.accounts() if acct.description == "Assets:Checking:Bar"
    )
    foo.download = Mock(
        side_effect=lambda *args, **kwargs: open(
            os.path.join("fixtures", "checking.ofx"), "rb"
        )
    )
    bar.download = Mock()
    config.accounts = Mock(return_value=[foo, bar])
    run(
        [
            "-l",
            os.path.join("fixtures", "checking.lgr"),
            "-a",
            "Assets:Savings:Foo",
        ],
        config,
    )
    foo.download.assert_has_calls([call(days=7)])
    bar.download.assert_not_called()


def test_find_ledger_path():
    os.environ["LEDGER_FILE"] = "/tmp/foo"
    assert (
        find_ledger_file() == "/tmp/foo"
    ), "Should use LEDGER_FILE to find ledger path."

    (f, tmprcpath) = tempfile.mkstemp(".ledgerrc")
    os.close(f)  # Who wants to deal with low-level file descriptors?
    with open(tmprcpath, "w") as f:
        f.write("--bar foo\n")
        f.write("--file /tmp/bar\n")
        f.write("--foo bar\n")
    assert (
        find_ledger_file(tmprcpath) == "/tmp/foo"
    ), "Should prefer LEDGER_FILE to --file arg in ledgerrc"
    del os.environ["LEDGER_FILE"]
    assert find_ledger_file(tmprcpath) == "/tmp/bar", "Should parse ledgerrc"
    os.unlink(tmprcpath)


def test_no_ledger_arg():
    with pytest.raises(LedgerAutosyncException):
        config = OfxConfig(os.path.join("fixtures", "ofxclient.ini"))
        run(["-l", os.path.join("fixtures", "checking.lgr"), "-L"], config)


def test_format_payee():
    with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
        run(
            [
                os.path.join("fixtures", "paypal.csv"),
                "-a",
                "Assets:Foo",
                "--payee-format",
                "GROSS:{Gross}",
                "-L",
            ]
        )
        assert re.search(r"GROSS:-20\.00", mock_stdout.getvalue())


# def test_multi_account():
#     with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
#         run([os.path.join('fixtures', 'multi_account.ofx'), '-a', 'Assets:Foo'])
#         self.assertRegexpMatches(mock_stdout.getvalue(), r"GROSS:-20\.00")


def test_no_ledger():
    config = OfxConfig(os.path.join("fixtures", "ofxclient.ini"))
    acct = config.accounts()[0]
    acct.download = Mock(
        side_effect=lambda *args, **kwargs: open(
            os.path.join("fixtures", "checking.ofx"), "rb"
        )
    )
    config.accounts = Mock(return_value=[acct])
    with patch("ledgerautosync.cli.find_ledger_file", return_value=None):
        with patch("sys.stderr", new_callable=StringIO) as mock_stdout:
            run([], config)
            assert (
                mock_stdout.getvalue()
                == "LEDGER_FILE environment variable not set, and no .ledgerrc file found, and -l argument was not supplied: running with deduplication disabled. All transactions will be printed!\n"
            )

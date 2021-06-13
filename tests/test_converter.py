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

import csv
import hashlib
import os
from decimal import Decimal

import pytest

from ledgerautosync.converter import (
    AmazonConverter,
    Amount,
    CsvConverter,
    MintConverter,
    PaypalAlternateConverter,
    PaypalConverter,
    Posting,
)


def test_format():
    assert (
        Posting("Foo", Amount(Decimal("10.00"), "$"), metadata={"foo": "bar"}).format(
            indent=2
        )
        == "  Foo                                                      $10.00\n  ; foo: bar\n"
    )


def test_amount():
    assert (
        "$10.00" == Amount(Decimal("10.001"), "$").format()
    ), "Formats to 2 points precision by default"
    assert (
        "10.00 USD" == Amount(Decimal(10), "USD").format()
    ), "Longer commodity names come after"
    assert (
        "-$10.00" == Amount(Decimal(10), "$", reverse=True).format()
    ), "Reverse flag works."
    assert (
        '10.00 "ABC123"' == Amount(Decimal(10), "ABC123").format()
    ), "Currencies with numbers are quoted"
    assert (
        '10.00 "A BC"' == Amount(Decimal(10), "A BC").format()
    ), "Currencies with whitespace are quoted"
    assert "$10.001" == Amount(Decimal("10.001"), "$", unlimited=True).format()


def test_get_csv_id():
    converter = CsvConverter(None)
    h = {"foo": "bar", "bar": "foo"}
    assert (
        converter.get_csv_id(h)
        == hashlib.md5("bar=foo\nfoo=bar\n".encode("utf-8")).hexdigest()
    )


@pytest.fixture
def reader(request):
    csv_name = request.node.get_closest_marker("csv_file").args[0]
    with open(os.path.join("fixtures", csv_name), "r") as csv_file:
        dialect = csv.Sniffer().sniff(csv_file.read(1024))
        csv_file.seek(0)
        dialect.skipinitialspace = True
        reader = csv.DictReader(csv_file, dialect=dialect)
        csv_file.seek(0)
        reader = csv.DictReader(csv_file, dialect=dialect)
        yield reader


@pytest.fixture
def converter(reader):
    return CsvConverter.make_converter(set(reader.fieldnames), reader.dialect, "Foo")


@pytest.mark.csv_file("paypal.csv")
def test_paypal_format(reader, converter):
    assert type(converter) == PaypalConverter
    assert (
        converter.convert(next(reader)).format()
        == """2016/06/04 Jane Doe someone@example.net My Friend ID: XYZ1, Recurring Payment Sent
    Foo                                                -20.00 USD
    ; csvid: paypal.XYZ1
    Expenses:Misc                                       20.00 USD
"""
    )
    assert (
        converter.convert(next(reader)).format()
        == """2016/06/04 Debit Card ID: XYZ2, Charge From Debit Card
    Foo                                               1120.00 USD
    ; csvid: paypal.XYZ2
    Transfer:Paypal                                  -1120.00 USD
"""
    )


@pytest.mark.csv_file("paypal_alternate.csv")
def test_paypal_alternate_format(reader, converter):
    assert type(converter) == PaypalAlternateConverter
    assert (
        converter.convert(next(reader)).format()
        == """2016/12/31 Some User: Payment Sent
    Foo                                                   -$12.34
    ; csvid: 1209a7bb0d17276248d463b71a6a8b8c
    Expenses:Misc                                          $12.34
"""
    )
    assert (
        converter.convert(next(reader)).format()
        == """2016/12/31 Bank Account: Add Funds from a Bank Account
    Foo                                                    $12.34
    ; csvid: 581e62da71bab74c7ce61854c2b6b6a5
    Transfer:Paypal                                       -$12.34
"""
    )


def test_mk_amount_alternate():
    converter = PaypalAlternateConverter(None)
    row = {"Currency": "USD", "Amount": "12.34"}
    assert converter.mk_amount(row) == Amount(Decimal("12.34"), "USD")


@pytest.mark.csv_file("amazon.csv")
def test_amazon_format(reader, converter):
    assert type(converter) == AmazonConverter
    assert (
        converter.convert(next(reader)).format()
        == """2016/01/29 Best Soap Ever
    Foo                                                    $21.90
    ; csvid: amazon.123-4567890-1234567
    ; url: https://www.amazon.com/gp/css/summary/print.html/ref=od_aui_print_invoice?ie=UTF8&orderID=123-4567890-1234567
    Expenses:Misc                                         -$21.90
"""
    )


@pytest.mark.csv_file("amazon2.csv")
def test_amazon2_format(reader, converter):
    assert type(converter) == AmazonConverter
    assert (
        converter.convert(next(reader)).format()
        == """2017/06/05 Test " double quote
    Foo                                                     $9.99
    ; csvid: amazon.111-1111111-1111111
    ; url: https://www.amazon.com/gp/css/summary/print.html/ref=od_aui_print_invoice?ie=UTF8&orderID=111-1111111-1111111
    Expenses:Misc                                          -$9.99
"""
    )


@pytest.mark.csv_file("mint.csv")
def test_mint_format(reader):
    converter = CsvConverter.make_converter(set(reader.fieldnames), reader.dialect)
    assert type(converter) == MintConverter
    assert (
        converter.convert(next(reader)).format()
        == """2016/08/02 Amazon
    1234                                                   $29.99
    ; csvid: mint.a7c028a73d76956453dab634e8e5bdc1
    Expenses:Shopping                                     -$29.99
"""
    )
    assert (
        converter.convert(next(reader)).format()
        == """2016/06/02 Autopay Rautopay Auto
    1234                                                 -$123.45
    ; csvid: mint.a404e70594502dd62bfc6f15d80b7cd7
    Credit Card Payment                                   $123.45
"""
    )

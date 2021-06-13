# Copyright (c) 2013-2021 Erik Hetzner
# Portions Copyright (c) 2016 James S Blachly, MD
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


import datetime
import hashlib
import re
from decimal import Decimal

from ofxparse.ofxparse import InvestmentTransaction
from ofxparse.ofxparse import Transaction as OfxTransaction

from ledgerautosync import EmptyInstitutionException

AUTOSYNC_INITIAL = "autosync_initial"
ALL_AUTOSYNC_INITIAL = "all.%s" % (AUTOSYNC_INITIAL)
UNKNOWN_BANK_ACCOUNT = "Assets:Unknown"


class EasyEquality(object):
    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self.__dict__ == other.__dict__
        else:
            return False

    def __ne__(self, other):
        return not self.__eq__(other)


class SecurityList(object):
    """
    The SecurityList represents the OFX <SECLIST>...</SECLIST>
    and holds securities present in the OFX records

    <SECINFO>...</SECINFO> as implemented by OFXparse only includes:
    {memo, name, ticker, uniqueid}
    Unfortunately does not provide uniqueid_type or currency

    It is iterable, and also provides lookup table (LUT) functionality
    provides __next__() for Py3
    """

    def __init__(self, ofx):
        securities = []
        if hasattr(ofx, "security_list") and ofx.security_list is not None:
            securities = ofx.security_list

        self.cusip_lut = dict()
        self.ticker_lut = dict()

        self._iter = iter(securities)
        self.securities = securities
        if len(securities) == 0:
            return

        # index
        for sec in securities:
            # unfortunately OFXparse does not currently implement
            # security.uniqueid_type so I am presuming here
            if sec.uniqueid:
                self.cusip_lut[sec.uniqueid] = sec
            if sec.ticker:
                self.ticker_lut[sec.ticker] = sec
            # This indexing strategy (whereby I index the object instead of
            # the inverse value (e.g. ticker symbol) directly has a flaw
            # in that an OFX file could define a security list section and
            # list CUSIPs without ticker property, or the converse

    def __iter__(self):
        return self

    def __next__(self):
        return next(self._iter)

    def __len__(self):
        return len(self.securities)

    # one possibility is to just implement __getitem__(),
    # however since OFXparse does not implement securitylist.security.uniqueid_type
    # I'll have no idea if what I am seeing is a CUSISP
    # unless I look it up specifically as a CUSIP (and it exists)
    def find_cusip(self, cusip):
        if cusip in self.cusip_lut:
            return self.cusip_lut[cusip]
        else:
            return None

    def find_ticker(self, ticker):
        if ticker in self.ticker_lut:
            return self.ticker_lut[ticker]
        else:
            return None


class Transaction(object):
    def __init__(
        self,
        date,
        payee,
        postings,
        checknum=None,
        cleared=False,
        metadata={},
        aux_date=None,
        date_format=None,
    ):
        self.date = date
        self.aux_date = aux_date
        self.payee = payee
        self.postings = postings
        self.metadata = metadata
        self.cleared = cleared
        self.date_format = date_format
        self.checknum = checknum

    def format(self, indent=4, assertions=True):
        retval = ""
        cleared_str = " "
        checknum_str = ""
        if self.cleared:
            cleared_str = " * "
        aux_date_str = ""
        if self.date_format is None:
            self.date_format = "%Y/%m/%d"
        if self.aux_date is not None:
            aux_date_str = "=%s" % (self.aux_date.strftime(self.date_format))
        if self.checknum is not None:
            checknum_str = " (%d)" % (self.checknum)
        retval += "%s%s%s%s%s\n" % (
            self.date.strftime(self.date_format),
            checknum_str,
            aux_date_str,
            cleared_str,
            self.payee,
        )
        for k in sorted(self.metadata.keys()):
            retval += "%s; %s: %s\n" % (" " * indent, k, self.metadata[k])
        for posting in self.postings:
            retval += posting.format(indent, assertions)
        return retval


class Posting(object):
    def __init__(self, account, amount, asserted=None, unit_price=None, metadata={}):
        self.account = account
        self.amount = amount
        self.asserted = asserted
        self.unit_price = unit_price
        self.metadata = metadata

    def format(self, indent=4, assertions=True):
        space_count = 65 - indent - len(self.account) - len(self.amount.format())
        if space_count < 2:
            space_count = 2
        retval = "%s%s%s%s" % (
            " " * indent,
            self.account,
            " " * space_count,
            self.amount.format(),
        )
        if assertions and self.asserted is not None:
            retval = "%s = %s" % (retval, self.asserted.format())
        if self.unit_price is not None:
            retval = "%s @ %s" % (retval, self.unit_price.format())
        retval += "\n"
        for k in sorted(self.metadata.keys()):
            retval += "%s; %s: %s\n" % (" " * indent, k, self.metadata[k])
        return retval

    def clone_inverted(self, account, asserted=None, metadata={}):
        return Posting(
            account,
            self.amount.clone_inverted(),
            asserted=asserted,
            unit_price=self.unit_price,
            metadata=metadata,
        )


class Amount(EasyEquality):
    def __init__(self, number, currency, reverse=False, unlimited=False):
        self.number = Decimal(number)
        self.reverse = reverse
        self.unlimited = unlimited
        self.currency = currency

    def format(self):
        # Commodities must be quoted in ledger if they have
        # whitespace or numerals.
        if re.search(r"[\s0-9]", self.currency):
            currency = '"%s"' % (self.currency)
        else:
            currency = self.currency
        if self.unlimited:
            number = str(abs(self.number))
        else:
            number = "%0.2f" % (abs(self.number))
        if self.number.is_signed() != self.reverse:
            prefix = "-"
        else:
            prefix = ""
        if len(currency) == 1:
            # $ comes before
            return "%s%s%s" % (prefix, currency, number)
        else:
            # USD comes after
            return "%s%s %s" % (prefix, number, currency)

    def clone_inverted(self):
        return Amount(
            self.number,
            self.currency,
            reverse=not (self.reverse),
            unlimited=self.unlimited,
        )


class Converter(object):
    @staticmethod
    def clean_id(id):
        return (
            id.replace("/", "_")
            .replace("$", "_")
            .replace(" ", "_")
            .replace("@", "_")
            .replace("*", "_")
            .replace("+", "_")
            .replace("&", "_")
            .replace("[", "_")
            .replace("]", "_")
            .replace("|", "_")
            .replace("%", "_")
        )

    def __init__(
        self,
        ledger=None,
        unknownaccount=None,
        currency="$",
        indent=4,
        payee_format=None,
        date_format=None,
        infer_account=True,
    ):
        self.lgr = ledger
        self.indent = indent
        self.unknownaccount = unknownaccount
        self.currency = currency.upper()
        self.payee_format = payee_format
        if self.currency == "USD":
            self.currency = "$"
        self.date_format = date_format
        self.infer_account = infer_account

    def mk_dynamic_account(self, payee, exclude):
        if self.lgr is None or not self.infer_account:
            return self.unknownaccount or "Expenses:Misc"
        else:
            account = self.lgr.get_account_by_payee(payee, exclude)
            if account is None:
                return self.unknownaccount or "Expenses:Misc"
            else:
                return account


class OfxConverter(Converter):
    def __init__(
        self,
        account,
        name,
        indent=4,
        ledger=None,
        fid=None,
        unknownaccount=None,
        payee_format=None,
        hardcodeaccount=None,
        shortenaccount=False,
        security_list=SecurityList([]),
        date_format=None,
        infer_account=True,
    ):
        super(OfxConverter, self).__init__(
            ledger=ledger,
            indent=indent,
            unknownaccount=unknownaccount,
            currency=account.statement.currency,
            payee_format=payee_format,
            date_format=date_format,
            infer_account=infer_account,
        )
        self.real_acctid = account.account_id
        if hardcodeaccount is not None:
            self.acctid = hardcodeaccount
        elif shortenaccount:
            self.acctid = account.account_id[-4:]
        else:
            self.acctid = account.account_id
        self.payee_format = payee_format
        self.security_list = security_list

        if fid is not None:
            self.fid = fid
        else:
            if account.institution is None:
                raise EmptyInstitutionException(
                    "Institution provided by OFX is empty and no fid supplied!"
                )
            else:
                self.fid = account.institution.fid
        self.name = name

    def mk_ofxid(self, txnid):
        if self.acctid != self.real_acctid:
            # Some banks insert the bank account number into the transaction ID
            # We will do this to properly hide the account number for privacy
            # reasons
            txnid = txnid.replace(self.real_acctid, self.acctid)
        return Converter.clean_id("%s.%s.%s" % (self.fid, self.acctid, txnid))

    def format_payee(self, txn):
        payee = ""
        if hasattr(txn, "payee") and txn.payee is not None:
            payee = txn.payee
        memo = ""
        if hasattr(txn, "memo") and txn.memo is not None:
            memo = txn.memo
        txntype = ""
        if hasattr(txn, "type") and txn.type is not None:
            txntype = txn.type
        tferaction = ""
        if hasattr(txn, "tferaction") and txn.tferaction is not None:
            tferaction = txn.tferaction.lower()

        if payee != "" and self.lgr is not None:
            payee = self.lgr.get_autosync_payee(payee, self.name)

        # If payee is blank but memo is not, then try matching Ledger payee
        # based on memo instead.
        if memo != "" and payee == "" and self.lgr is not None:
            memo = self.lgr.get_autosync_payee(memo, self.name)

        payee_format = self.payee_format

        if payee_format is None:
            # Default when not provided
            payee_format = "{payee} {memo}"

            # Alternate for when payee and memo are blank, sometimes true for
            # investment accounts.
            if (payee == "") and (memo == ""):
                payee_format = "{account}: {txntype}"
                if tferaction != "":
                    payee_format += ": {tferaction}"

            # Sometimes memo/payee are simply longer versions of the other.
            if memo.startswith(payee):
                payee = ""
            if payee.startswith(memo):
                memo = ""

        return payee_format.format(
            payee=payee,
            memo=memo,
            txntype=txntype,
            account=self.name,
            tferaction=tferaction,
        ).strip()

    def format_balance(self, statement):
        # Get date. Ensure the date is a date-like object.
        if hasattr(statement, "balance_date") and hasattr(
            statement.balance_date, "strftime"
        ):
            date = statement.balance_date
        elif hasattr(statement, "end_date") and hasattr(statement.end_date, "strftime"):
            date = statement.end_date
        else:
            return ""
        if hasattr(statement, "balance"):
            return Transaction(
                date=date,
                cleared=True,
                payee="--Autosync Balance Assertion",
                postings=[
                    Posting(
                        self.name,
                        Amount(Decimal("0"), currency=self.currency),
                        asserted=Amount(statement.balance, self.currency),
                    )
                ],
                date_format=self.date_format,
            ).format(self.indent)
        else:
            return ""

    def format_initial_balance(self, statement):
        if hasattr(statement, "balance"):
            initbal = statement.balance
            for txn in statement.transactions:
                initbal -= txn.amount

            posting = Posting(
                self.name,
                Amount(initbal, currency=self.currency),
                metadata={"ofxid": self.mk_ofxid(AUTOSYNC_INITIAL)},
            )

            return Transaction(
                date=statement.start_date,
                payee="--Autosync Initial Balance",
                cleared=True,
                postings=[
                    posting,
                    posting.clone_inverted("Assets:Equity").format(self.indent),
                ],
                date_format=self.date_format,
            ).format(self.indent)
        else:
            return ""

    # Return the ticker symbol of the security with CUSIP, if it exists in the
    # security_list mapping. Otherwise, simply return the CUSIP.
    def maybe_get_ticker(self, cusip):
        security = self.security_list.find_cusip(cusip)
        if security and security.ticker:
            return security.ticker
        else:
            return cusip

    def convert(self, txn):
        """
        Convert an OFX Transaction to a Transaction
        """

        ofxid = self.mk_ofxid(txn.id)
        metadata = {}
        posting_metadata = {"ofxid": ofxid}

        if isinstance(txn, OfxTransaction):
            posting = Posting(
                self.name, Amount(txn.amount, self.currency), metadata=posting_metadata
            )
            checknum = None
            if hasattr(txn, "checknum") and txn.checknum != "":
                checknum = int(txn.checknum)
            return Transaction(
                date=txn.date,
                payee=self.format_payee(txn),
                postings=[
                    posting,
                    posting.clone_inverted(
                        self.mk_dynamic_account(
                            self.format_payee(txn), exclude=self.name
                        )
                    ),
                ],
                date_format=self.date_format,
                checknum=checknum,
            )
        elif isinstance(txn, InvestmentTransaction):
            acct1 = self.name
            acct2 = self.name

            posting1 = None
            posting2 = None

            security = self.maybe_get_ticker(txn.security)

            if isinstance(txn.type, str):
                # recent versions of ofxparse
                if re.match("^(buy|sell)", txn.type):
                    acct2 = self.unknownaccount or "Assets:Unknown"
                elif txn.type == "transfer":
                    acct2 = "Transfer"
                elif txn.type == "reinvest":
                    # reinvestment of income
                    # TODO: make this configurable
                    acct2 = "Income:Interest"
                elif txn.type == "income" and txn.income_type == "DIV":
                    # Fidelity lists non-reinvested dividend income as
                    # type: income, income_type: DIV
                    # TODO: determine how dividend income is listed from other institutions
                    # income/DIV transactions do not involve buying or selling a security
                    # so their postings need special handling compared to
                    # others
                    metadata["dividend_from"] = security
                    acct2 = "Income:Dividends"
                    posting1 = Posting(
                        acct1,
                        Amount(txn.total, self.currency),
                        metadata=posting_metadata,
                    )
                    posting2 = posting1.clone_inverted(acct2)
                else:
                    # ???
                    pass
            else:
                # Old version of ofxparse
                if txn.type in [0, 1, 3, 4]:
                    # buymf, sellmf, buystock, sellstock
                    acct2 = self.unknownaccount or "Assets:Unknown"
                elif txn.type == 2:
                    # reinvest
                    acct2 = "Income:Interest"
                else:
                    # ???
                    pass

            aux_date = None
            if txn.settleDate is not None and txn.settleDate != txn.tradeDate:
                aux_date = txn.settleDate

            # income/DIV already defined above;
            # this block defines all other posting types
            if posting1 is None and posting2 is None:
                posting_list = self._finalize_postings(
                    acct1, acct2, txn, security, posting_metadata
                )
            else:
                # Previously defined if type:income income_type/DIV
                posting_list = [posting1, posting2]

            return Transaction(
                date=txn.tradeDate,
                aux_date=aux_date,
                payee=self.format_payee(txn),
                metadata=metadata,
                postings=posting_list,
                date_format=self.date_format,
            )

    def _finalize_postings(self, acct1, acct2, txn, security, posting_metadata):
        """Finalize postings to include fees and other post-processing

        :param acct1:  Account for first posting.

        :param acct2:  Account for second posting.

        :param txn:    Instance of Transaction we are working on.

        :param security: security element we are working on.

        :param posting_metadata:  Posting metadata

        ~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-

        :return:  A list of Posting instances for txn.

        ~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-

        PURPOSE:  This method finalizes the postings for txn. We need
                  this because sometimes the postings are more complicated
                  (e.g., if we have fees or commissions for a stock trade).
                  See https://github.com/egh/ledger-autosync/issues/109.
        """
        posting_list = []
        posting_list.append(
            Posting(
                acct1,
                Amount(txn.units, security, unlimited=True),
                unit_price=Amount(txn.unit_price, self.currency, unlimited=True),
                metadata=posting_metadata,
            )
        )
        posting_list.append(
            Posting(
                acct2,
                Amount(
                    txn.units * txn.unit_price + txn.fees, self.currency, reverse=True
                ),
            )
        )
        if txn.fees:
            posting_list.append(
                Posting("Expenses:Fees", Amount(txn.fees, self.currency))
            )
        if txn.commission:
            posting_list.append(
                Posting("Expenses:Commission", Amount(txn.commission, self.currency))
            )

        return posting_list

    def format_position(self, pos):
        if (
            hasattr(pos, "date")
            and hasattr(pos, "security")
            and hasattr(pos, "unit_price")
        ):
            dateStr = pos.date.strftime("%Y/%m/%d %H:%M:%S")
            return "P %s %s %s\n" % (
                dateStr,
                self.maybe_get_ticker(pos.security),
                pos.unit_price,
            )


class CsvConverter(Converter):
    @staticmethod
    def make_converter(fieldset, dialect, name=None, **kwargs):
        for klass in CsvConverter.descendants():
            if klass.FIELDSET <= fieldset:
                return klass(dialect, name=name, **kwargs)
        # Found no class, bail
        raise Exception("Cannot determine CSV type")

    @classmethod
    def descendants(cls):
        retval = cls.__subclasses__()
        for cls2 in cls.__subclasses__():
            retval.extend(cls2.descendants())
        return retval

    # By default, return an MD5 of the key-value pairs in the row.
    # If a better ID is available, should be overridden.
    def get_csv_id(self, row):
        h = hashlib.md5()
        for key in sorted(row.keys()):
            h.update(("%s=%s\n" % (key, row[key])).encode("utf-8"))
        return h.hexdigest()

    def __init__(
        self,
        dialect,
        name=None,
        indent=4,
        ledger=None,
        unknownaccount=None,
        payee_format=None,
        date_format=None,
        infer_account=True,
    ):
        super(CsvConverter, self).__init__(
            ledger=ledger,
            indent=indent,
            unknownaccount=unknownaccount,
            payee_format=payee_format,
            date_format=date_format,
            infer_account=infer_account,
        )
        self.name = name
        self.dialect = dialect

    def format_payee(self, row):
        return re.sub(r"\s+", " ", self.payee_format.format(**row).strip())


class PaypalConverter(CsvConverter):
    FIELDSET = {
        "Currency",
        "Date",
        "Gross",
        "Item Title",
        "Name",
        "Net",
        "Status",
        "To Email Address",
        "Transaction ID",
        "Type",
    }

    def __init__(self, *args, **kwargs):
        super(PaypalConverter, self).__init__(*args, **kwargs)
        if self.payee_format is None:
            self.payee_format = (
                "{Name} {To Email Address} {Item Title} ID: {Transaction ID}, {Type}"
            )

    def get_csv_id(self, row):
        return "paypal.%s" % (Converter.clean_id(row["Transaction ID"]))

    def convert(self, row):
        if (
            (row["Status"] != "Completed")
            and (row["Status"] != "Refunded")
            and (row["Status"] != "Reversed")
        ) or (row["Type"] == "Shopping Cart Item"):
            return ""
        else:
            currency = row["Currency"]
            posting_metadata = {"csvid": self.get_csv_id(row)}
            net = Decimal(row["Net"].replace(",", ""))
            gross = Decimal(row["Gross"].replace(",", ""))

            if (
                row["Type"] == "Add Funds from a Bank Account"
                or row["Type"] == "Charge From Debit Card"
            ):
                posting = Posting(
                    self.name, Amount(net, currency), metadata=posting_metadata
                )
                postings = [posting, posting.clone_inverted("Transfer:Paypal")]
            else:
                posting = Posting(
                    self.name, Amount(gross, currency), metadata=posting_metadata
                )
                postings = [
                    posting,
                    # TODO Our payees are breaking the payee search in
                    # mk_dynamic_account
                    # self.mk_dynamic_account(payee, exclude=self.name),
                    posting.clone_inverted("Expenses:Misc"),
                ]
            return Transaction(
                date=datetime.datetime.strptime(row["Date"], "%m/%d/%Y"),
                payee=self.format_payee(row),
                postings=postings,
                date_format=self.date_format,
            )


# Apparently Paypal has another CSV


class PaypalAlternateConverter(CsvConverter):
    FIELDSET = {"Date", "Name", "Type", "Status", "Amount"}

    def __init__(self, *args, **kwargs):
        super(PaypalAlternateConverter, self).__init__(*args, **kwargs)
        if self.payee_format is None:
            self.payee_format = "{Name}: {Type}"

    def mk_amount(self, row, reverse=False):
        currency = "$"
        if "Currency" in row:
            currency = row["Currency"]
        return Amount(
            Decimal(re.sub(r"\$", "", row["Amount"])), currency, reverse=reverse
        )

    def convert(self, row):
        if (
            (row["Status"] != "Completed")
            and (row["Status"] != "Refunded")
            and (row["Status"] != "Reversed")
        ) or (row["Type"] == "Shopping Cart Item"):
            return ""
        else:
            posting_metadata = {"csvid": self.get_csv_id(row)}
            posting = Posting(self.name, self.mk_amount(row), metadata=posting_metadata)
            if (
                row["Type"] == "Add Funds from a Bank Account"
                or row["Type"] == "Charge From Debit Card"
            ):

                posting2_account = "Transfer:Paypal"
            else:
                posting2_account = "Expenses:Misc"
            return Transaction(
                date=datetime.datetime.strptime(row["Date"], "%m/%d/%Y"),
                payee=self.format_payee(row),
                postings=[posting, posting.clone_inverted(posting2_account)],
                date_format=self.date_format,
            )


class AmazonConverter(CsvConverter):
    FIELDSET = {"Currency", "Title", "Order Date", "Order ID"}

    def __init__(self, *args, **kwargs):
        super(AmazonConverter, self).__init__(*args, **kwargs)
        self.dialect.doublequote = True

    def mk_amount(self, row, reverse=False):
        currency = row["Currency"]
        if currency == "USD":
            currency = "$"
        return Amount(
            Decimal(re.sub(r"\$", "", row["Item Total"])), currency, reverse=reverse
        )

    def get_csv_id(self, row):
        return "amazon.%s" % (Converter.clean_id(row["Order ID"]))

    def convert(self, row):
        posting = Posting(
            self.name,
            self.mk_amount(row),
            metadata={
                "url": "https://www.amazon.com/gp/css/summary/print.html/ref=od_aui_print_invoice?ie=UTF8&orderID=%s"
                % (row["Order ID"]),  # noqa E501
                "csvid": self.get_csv_id(row),
            },
        )

        return Transaction(
            date=datetime.datetime.strptime(row["Order Date"], "%m/%d/%y"),
            payee=row["Title"],
            postings=[posting, posting.clone_inverted("Expenses:Misc")],
            date_format=self.date_format,
        )


class MintConverter(CsvConverter):
    FIELDSET = {
        "Date",
        "Amount",
        "Description",
        "Account Name",
        "Category",
        "Transaction Type",
    }

    def __init__(self, *args, **kwargs):
        super(MintConverter, self).__init__(*args, **kwargs)

    def mk_amount(self, row, reverse=False):
        return Amount(Decimal(row["Amount"]), "$", reverse=reverse)

    def convert(self, row):
        account = self.name
        if account is None:
            account = row["Account Name"]
        postings = []
        posting_metadata = {"csvid": "mint.%s" % (self.get_csv_id(row))}
        if row["Transaction Type"] == "credit":
            posting = Posting(
                account, self.mk_amount(row, reverse=True), metadata=posting_metadata
            )
            postings = [posting, posting.clone_inverted(row["Category"])]
        else:
            posting = Posting(account, self.mk_amount(row), metadata=posting_metadata)
            postings = [
                posting,
                posting.clone_inverted("Expenses:%s" % (row["Category"])),
            ]

        return Transaction(
            date=datetime.datetime.strptime(row["Date"], "%m/%d/%Y"),
            payee=row["Description"],
            postings=postings,
            date_format=self.date_format,
        )


# Simple.com
class SimpleConverter(CsvConverter):
    FIELDSET = {
        "Date",
        "Recorded at",
        "Scheduled for",
        "Amount",
        "Activity",
        "Pending",
        "Raw description",
        "Description",
        "Category folder",
        "Category",
        "Street address",
        "City",
        "State",
        "Zip",
        "Latitude",
        "Longitude",
        "Memo",
    }

    def __init__(self, *args, **kwargs):
        super(SimpleConverter, self).__init__(*args, **kwargs)

    def convert(self, row):
        amount = abs(float(row["Amount"]))
        reverse = row["Amount"][0] == "-"

        if reverse:
            account = "Expenses:%s" % (row["Category"])
        else:
            account = "Income:%s" % (row["Category"])

        posting_metadata = {
            "csvid": "simple.%s" % (self.get_csv_id(row)),
            "raw_description": row["Raw description"],
            "activity_type": row["Activity"],
        }
        if row["Memo"]:
            posting_metadata["memo"] = row["Memo"]

        return Transaction(
            date=datetime.datetime.strptime(row["Date"], "%Y/%m/%d"),
            payee=row["Description"],
            postings=[
                Posting(
                    self.name, Amount(amount, "$", reverse), metadata=posting_metadata
                ),
                Posting(account, Amount(amount, "$", reverse=not (reverse))),
            ],
            date_format=self.date_format,
        )


class VenmoConverter(CsvConverter):
    FIELDSET = set(
        [
            "Username",
            "ID",
            "Datetime",
            "Type",
            "Status",
            "Note",
            "From",
            "To",
            "Amount (total)",
            "Amount (fee)",
            "Funding Source",
            "Destination",
            "Beginning Balance",
            "Ending Balance",
            "Statement Period Venmo Fees",
            "Year to Date Venmo Fees",
            "Disclaimer",
        ]
    )

    def __init__(self, *args, **kwargs):
        # Initialize max date to be used for balance assertion
        self.max_date = datetime.datetime.min
        super(VenmoConverter, self).__init__(*args, **kwargs)

    def convert(self, row):

        # Venmo has a hierarchical structure with some rows containing
        # statement level data
        if not row["ID"]:
            if row["Ending Balance"]:
                # This relies `self.max_date` being correct, which in turn
                # relies on the statement balance being after all transactions.
                # This seems to be how the statement is currently formatted but
                # may break if Venmo changes format
                return Transaction(
                    date=self.max_date,
                    cleared=True,
                    payee="--Autosync Balance Assertion",
                    postings=[
                        Posting(
                            self.name,
                            Amount(Decimal("0"), currency=self.currency),
                            asserted=Amount(
                                row["Ending Balance"].replace("$", "").replace(",", ""),
                                self.currency,
                            ),
                        )
                    ],
                    date_format=self.date_format,
                ).format(self.indent)
            else:
                return ""

        md = re.match(r"^([+-]) \$([0-9,\.]+)", row["Amount (total)"])
        amount = md.group(2).replace(",", "")
        if md.group(1) == "-":
            reverse = True
            account = self.unknownaccount or "expenses"
        else:
            reverse = False
            account = self.unknownaccount or "income"

        if row["Type"] == "Payment":
            if reverse:
                payee = row["To"]
            else:
                payee = row["From"]
        else:
            if reverse:
                payee = row["From"]
            else:
                payee = row["To"]
        date = datetime.datetime.strptime(row["Datetime"], "%Y-%m-%dT%H:%M:%S")
        if date > self.max_date:
            self.max_date = date

        return Transaction(
            date=date,
            payee=payee,
            metadata={"desc": row["Note"]},
            postings=[
                Posting(
                    self.name,
                    Amount(amount, "$", reverse=reverse),
                    metadata={"csvid": self.get_csv_id(row)},
                ),
                Posting(account, Amount(amount, "$", reverse=not (reverse))),
            ],
            date_format=self.date_format,
        )

    def get_csv_id(self, row):
        return "venmo.{}".format(Converter.clean_id(row["ID"]))

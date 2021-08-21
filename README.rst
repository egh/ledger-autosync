ledger-autosync
===============

.. image:: https://travis-ci.org/egh/ledger-autosync.svg?branch=master
  :target: https://travis-ci.org/egh/ledger-autosync

ledger-autosync is a program to pull down transactions from your bank
and create `ledger <http://ledger-cli.org/>`__ transactions for them.
It is designed to only create transactions that are not already
present in your ledger files (that is, it will deduplicate
transactions). This should make it comparable to some of the automated
synchronization features available in products like GnuCash, Mint,
etc. In fact, ledger-autosync performs OFX import and synchronization
better than all the alternatives I have seen.

News
----

v1.0.0
~~~~~~

Versions of ledger-autosync before 1.0.0 printed the ofxid in a
slightly incorrect position. This should not effect usage of the
program, but if you would like to correct the error, see below for
more details.

Features
--------

-  supports `ledger <http://ledger-cli.org/>`__ 3 and
   `hledger <http://hledger.org/>`__
-  like ledger, ledger-autosync will never modify your files directly
-  interactive banking setup via
   `ofxclient <https://github.com/captin411/ofxclient>`__
-  multiple banks and accounts
-  support for non-US currencies
-  support for 401k and investment accounts

   -  tracks investments by share, not dollar value
   -  support for complex transaction types, including transfers, buys,
      sells, etc.

-  import of downloaded OFX files, for banks not supporting automatic
   download
-  import of downloaded CSV files from Paypal, Simple, Amazon and Mint
-  any CSV file can be supported via plugins

Platforms
---------

ledger-autosync is developed on Linux with ledger 3 and python 3; it
has been tested on Windows (although it will run slower) and should
run on OS X. It requires ledger 3 or hledger, but it should run faster
with ledger, because it will not need to start a command to check
every transaction.


Quickstart
----------

Installation
~~~~~~~~~~~~

If you are on Debian or Ubuntu, an (older) version of ledger-autosync
should be available for installation. Try:

::

    $ sudo apt-get install ledger-autosync

If you use pip, you can install the latest released version:

::

    $ pip install ledger-autosync

You can also install from source, if you have downloaded the source:

::

    $ python setup.py install

You may need to install the following libraries (on debian/ubuntu):

::

    $ sudo apt-get install libffi-dev libpython-dev libssl-dev libxml2-dev python-pip libxslt-dev

Running
~~~~~~~

Once you have ledger-autosync installed, you can download an OFX file
from your bank and run ledger-autosync against it:

::

    $ ledger-autosync download.ofx

This should print a number of transactions to stdout. If you add these
transactions to your default ledger file (whatever is read when you
run ``ledger`` without arguments), you should find that if you run
ledger-autosync again, it should print no transactions. This is
because of the deduplicating feature: only new transactions will be
printed for insertion into your ledger files.

Using the ofx protocol for automatic download
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

ledger-autosync also supports using the OFX protocol to automatically
connect to banks and download data. You can use the ofxclient program
(which should have been installed with ledger-autosync) to set up
banking:

::

    $ ofxclient

When you have added your institution, quit ofxclient.

(At least one user has reported being signed up for a pay service by
setting up OFX direct connect. Although this seems unusual, please be
aware of this.)

Edit the generated ``~/ofxclient.ini`` file. Change the
``description`` field of your accounts to the name used in ledger.
Optionally, move the ``~/ofxclient.ini`` file to your ``~/.config``
directory.

Run:

::

    ledger-autosync

This will download a maximum of 90 days previous activity from your
accounts. The output will be in ledger format and printed to stdout.
Add this output to your ledger file. When that is done, you can call:

::

    ledger-autosync

again, and it should print nothing to stdout, because you already have
those transactions in your ledger.

How it works
------------

ledger-autosync stores a unique identifier as metadata with each
transaction. (For OFX files, this is a unique ID provided by your
institution for each transaction.) When syncing with your bank, it
will check if the transaction exists by running the ledger or hledger
command. If the transaction exists, it does nothing. If it does not
exist, the transaction is printed to stdout.

Payee matching
~~~~~~~~~~~~~~

When generating transactions, ledger-autosync attempts to match
previous payees to determine the appropriate accounts. For instance,
if a previous payee was ``Grocery store``, and one posting was to the
account ``Expenses:Food``, ledger-autosync will use that account again.
If ledger-autosync can’t find a matching payee, it will use
``Expenses:Misc`` or the value of the ``--unknown-account`` argument.

The matching is not very sophisticated: it only does exact matching on
the payee, and it uses transaction with the matching payee. It is also
not currently working with CSV files.

If you prefer to modify the payees to make them shorter than what is
generated by ledger-autosync, you can use the ``AutosyncPayee`` metadata
field to indicate to ledger-autosync that it should use the longer
form for matching. For instance:

::

    2011/03/31 Grocery
      ; AutosyncPayee: Payment to Grocery store #12345 CALIFORNIA
      Assets:Bank                                  -$0.01
      Expenses:Food                                 $0.01

would indicate to ledger-autosync that any payee with the name
``Payment to Grocery store #12345 CALIFORNIA`` should use the
``Expenses:Food`` account.

ofxid/csvid metadata tag
~~~~~~~~~~~~~~~~~~~~~~~~

ledger-autosync stores a metatag with every posting that it outputs to
support deduplication. This metadata tag is either ``ofxid`` (for OFX
imports) or ``csvid`` for CSV imports.

Pre-1.0.0 versions of ledger-autosync put this metadata tag in a
slightly incorrect place, associating the metadata tag with the
transaction itself, and not simply one posting. This should not effect
the usage of ledger-autosync, but if you would like to correct your
ledger files, there is a small python script ``fix_ofxid.py`` included
with ledger-autosync. It can be run as:

::

   python fix_ofxid.py <input file>

and will print a corrected file to stdout.

Syncing a CSV file
------------------

If you have a CSV file, you may also be able to import it using a
recent (installed via source) version of ledger-autosync.
ledger-autosync can currently process CSV files as provided by Paypal,
Amazon, or Mint. You can process the CSV file as follows:

::

    ledger-autosync /path/to/file.csv -a Assets:Paypal

With Amazon and Paypal CSV files, each row includes a unique
identifier, so ledger-autosync will be able to deduplicate against any
previously imported entries in your ledger files.

With Mint, a unique identifier based on the data in the row is
generated and stored. If future downloads contain identical rows, they
will be deduplicated. This method is probably not as robust as a
method based on unique ids, but Mint does not provide a unique id, and
it should be better than nothing. It is likely to generate false
negatives: transactions that seem new, but are in fact old. It will
not generate false positives: transactions that are not generated
because they seem old.

If you are a developer, you should fine it easy enough to add a new
CSV format to ledger-autosync. See, for example, the ``MintConverter``
class in the ``ledgerautosync/converter.py`` file in this repository.
See below for how to add these as plugins.

Assertions
----------

If you supply the ``--assertions`` flag, ledger-autosync will also
print out valid ledger assertions based on your bank balances at the
time of the sync. These otherwise empty transactions tell ledger that
your balance *should* be something at a given time, and if not, ledger
will fail with an error.

401k and investment accounts
----------------------------

If you have a 401k account, ledger-autosync can help you to track the
state of it. You will need OFX files (or an OFX protocol connection as
set up by ofxclient) provided by your 401k.

In general, your 401k account will consist of buy transactions,
transfers and reinvestments. The type will be printed in the payee
line after a colon (``:``)

The buy transactions are your contributions to the 401k. These will be
printed as follows:

::

    2016/01/29 401k: buymf
      Assets:Retirement:401k                                 1.12345 FOOBAR @ $123.123456
      ; ofxid: 1234
      Income:Salary                                            -$138.32

This means that you bought (contributed) $138.32 worth of FOOBAR (your
investment fund) at the price of $123.123456. The money to buy the
investment came from your income. In ledger-autosync, the
``Assets:Retirement:401k`` account is the one specified using the
``--account`` command line, or configured in your ``ofxclient.ini``.
The ``Income:Salary`` is specified by the ``--unknown-account``
option.

If the transaction is a “transfer” transaction, this usually means
either a fee or a change in your investment option:

::

    2014/06/30 401k: transfer: out
      Assets:Retirement:401k                                -1.61374 FOOBAR @ $123.123456
      ; ofxid: 1234
      Transfer                                                  $198.69

You will need to examine your statements to determine if this was a
fee or a real transfer back into your 401k.

Another type of transaction is a “reinvest” transaction:

::

    2014/06/30 401k: reinvest
      Assets:Retirement:401k                                0.060702 FOOBAR @ $123.123456
      ; ofxid: 1234
      Income:Interest                                            -$7.47

This probably indicates a reinvestment of dividends. ledger-autosync
will print ``Income:Interest`` as the other account.

resync
------

By default, ledger-autosync will process transactions backwards, and
stop when it sees a transaction that is already in ledger. To force it
to process all transactions up to the ``--max`` days back in time
(default: 90), use the ``--resync`` option. This can be useful when
increasing the ``--max`` option. For instance, if you previously
synchronized 90 days and now want to get 180 days of transactions,
ledger-autosync would stop before going back to 180 days without the
``--resync`` option.

payee format
------------

By default, ledger-autosync attempts to generate a decent payee line
(the information that follows the date in a ledger transaction).
Unfortunately, because of differences in preference and in the format
of OFX files, it is not always possible to generate the user’s
preferred payee format. ledger-autosync supports a ``payee-format``
option that can be used to generate your preferred payee line. This
option is of the format ``Text {memo}``, where ``memo`` is a
substitution based on the value of the transaction. Available
substitutions are ``memo``, ``payee``, ``txntype``, ``account`` and
``tferaction``. For example:

::

   $ ledger-autosync --payee-format "Memo: {memo}"
   2011/03/31 Memo: DIVIDEND EARNED FOR PERIOD OF 03/01/2011 THROUGH 03/31/2011 ANNUAL PERCENTAGE YIELD EARNED IS 0.05%

This option is also available for CSV conversion. For CSV files, you
can substitution any of the values of the rows in the CSV file by
name. For instance, for Paypal files:

::

   $ ledger-autosync --payee-format "{Name} ({To Email Address})" -a Paypal paypal.csv
   2016/06/04 Jane Doe (someone@example.net)

python bindings
---------------

If the ledger python bindings are available, ledger-autosync can use
them if you pass in the ``--python`` argument. Note, however, they can
be buggy, which is why they are disabled by default

Plugin support
--------------

ledger-autosync has support for plugins. By placing python files a
directory named ``~/.config/ledger-autosync/plugins/`` it should be
possible to automatically load python files from there. You may place
``CsvCconverter`` subclasses here, which will be selected based on the
columns in the CSV file being parsed and the FIELDSET of the CSV
converters. You may also place a single ``OfxConverter`` in the plugin
directory, which will be used in place of the stock ``OfxConverter``.

Below is an example CSV converter, starting with the input CSV file:

::

    "Date","Name","Amount","Balance"
    "11/30/2016","Dividend","$1.06","$1,000“

The following converter in the file ``~/.config/ledger-autosync/plugins/my.py``:

::

    from ledgerautosync.converter import CsvConverter, Posting, Transaction, Amount
    import datetime
    import re

    class SomeConverter(CsvConverter):
        FIELDSET = set(["Date", "Name", "Amount", "Balance"])

        def __init__(self, *args, **kwargs):
            super(SomeConverter, self).__init__(*args, **kwargs)

        def convert(self, row):
            md = re.match(r"^(\(?)\$([0-9,\.]+)", row['Amount'])
            amount = md.group(2).replace(",", "")
            if md.group(1) == "(":
                reverse = True
            else:
                reverse = False
            if reverse:
                account = 'expenses'
            else:
                account = 'income'
            return Transaction(
                date=datetime.datetime.strptime(row['Date'], "%m/%d/%Y"),
                payee=row['Name'],
                postings=[Posting(self.name, Amount(amount, '$', reverse=reverse)),
                          Posting(account, Amount(amount, '$', reverse=not(reverse)))])

Running ``ledger-autosync file.csv -a assets:bank`` will generate:

::

    2016/11/30 Dividend
        assets:bank                                $1.06
        income                                    -$1.06

For more examples, see
https://gitlab.com/egh/ledger-autosync/blob/master/ledgerautosync/converter.py#L421
or the `example plugins directory <examples/plugins>`_.

If you develop a converter that you think will be generally
useful, please consider submitting a pull request.

Testing
-------

ledger-autosync uses pytest for tests. To test, run pytest in the project directory. This will test the ledger, hledger and ledger-python interfaces. If hledger or the ledger-python interface is not found, these tests will be skipped.

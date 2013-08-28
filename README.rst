=================
 ledger-autosync
=================

ledger-autosync is a program to pull down transactions from your bank
and create ledger_ transactions for them. It is designed to only
create transactions that are not already present in your ledger files.
This should make it comparable to some of the automated
synchronization features available in products like GnuCash, Mint,
etc.

Features
--------

- supports ledger_ and hledger_
- like ledger, ledger-autosync will never modify your files directly
- interactive banking setup via ofxclient [1]
- multiple banks and accounts
- import of downloaded OFX files, for banks not supporting automatic
  download

Quickstart
----------

Install::

  $ python setup.py install

Run ofxclient to set up banking::

  $ ofxclient

When you have added your institution, quit ofxclient.

Edit the generated ``~/ofxclient.ini`` file. Change the
``description`` field of your accounts to the name used in ledger.

Run::

  ledger-autosync

This will download a maximum of 90 days previous activity from your
accounts. The output will be in ledger format and printed to stdout.
Add this output to your ledger file. When that is done, you can call::

  ledger-autosync

again, and it should print nothing to stdout, because you already have
those transactions in your ledger.

resync
~~~~~~

By default, ledger-autosync will process transactions backwards, and
stop when it sees a transaction that is already in ledger. To force it
to process all transactions up to the ``--max`` days back in time
(default: 90), use the ``--resync`` option. This can be useful when
increasing the ``--max`` option. For instance, if you previously
synchronized 90 days and now want to get 180 days of transactions,
ledger-autosync would stop before going back to 180 days without the
``--resync`` option.

Syncing a file
--------------

Some banks allow users to download OFX files, but do not support
fetching via the OFX protocol. If you have an OFX file, you can
convert to ledger::

  ledger-autosync /path/to/file.ofx

This will print unknown transactions in the file to stdout in the same
way as ordinary sync. If the transaction is already in your ledger, it
will be ignored.

How it works
------------

ledger-autosync stores a unique identifier, provided by your
institution for each transaction, as metadata in each transaction.
When syncing with your bank, it will check if the transaction exists
by running the ledger or hledger command. If the transaction exists,
it does nothing. If it does not exist, the transaction is printed to
stdout.

.. _ledger: http://ledger-cli.org/
.. _hledger: http://hledger.org/
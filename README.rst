=================
 ledger-autosync
=================

Automatically sync your transactions with your `ledger <http://ledger-cli.org/>`_.

Quickstart
----------

Install::

  $ python setup.py install

Run ofxclient to set up banking::

  $ ofxclient

When you have added your institution, quit ofxclient.

Edit the generated ``~/ofxclient.ini`` file. Change the
``description`` field of your accounts to the name used in ``ledger``.

Run::

  ledger-autosync --max 7

This will download a maximum of 7 days previous activity from your
accounts. The output will be in ledger format and printed to stdout.
Add this output to your ledger file. When that is done, you can call::

  ledger-autosync --max 7

again, and it should print nothing to stdout, because you already have
those transactions in your ledger.

How it works
------------

``ledger-autosync`` stores a unique identifier, provided by your
institution for each transaction, as metadata in each transaction.
When syncing with your bank, it will check if the transaction exists
by running the ``ledger`` command. If the transaction exists, it does
nothing. If it does not exist, the transaction is printed to stdout.
# ledger-autosync

ledger-autosync is a program to pull down transactions from your bank and create
[ledger](http://ledger-cli.org/) transactions for them. It is designed to only
create transactions that are not already present in your ledger files (that is,
deduplicate transactions). This should make it comparable to some of the
automated synchronization features available in products like GnuCash, Mint,
etc. In fact, ledger-autosync performs OFX import and synchronization better
than all the alternatives I have seen.

## Features

-   supports [ledger](http://ledger-cli.org/) 3 and
    [hledger](http://hledger.org/)
-   like ledger, ledger-autosync will never modify your files directly
-   interactive banking setup via
    [ofxclient](https://github.com/captin411/ofxclient)
-   multiple banks and accounts
-   support for non-US currencies
-   support for 401k and investment accounts
    -   tracks investments by share, not dollar value
    -   support for complex transaction types, including transfers, buys, sells,
        etc.
-   import of downloaded OFX files, for banks not supporting automatic
    download
-   import of downloaded CSV files from Paypal, Amazon and Mint

## Platforms

ledger-autosync is developed on Linux with ledger 3; it has been tested
on Windows (although it will run slower) and should run on OS X. It
requires ledger 3 or hledger, but it should run faster with ledger,
because it will not need to start a command to check every transaction.

## Quickstart

### Installation

If you are on Debian or Ubuntu, an (older) version of ledger-autosync should be
available for installation. Try:

    $ sudo apt-get install ledger-autosync

If you use pip, you can install the latest released version:

    $ pip install ledger-autosync

You can also install from source, if you have downloaded the source:

    $ python setup.py install

### Running

Once you have ledger-autosync installed, you can download an OFX file from your
bank and run ledger-autosync against it:

    $ ledger-autosync download.ofx

This should print a number of transactions to stdout. If you add these
transactions to your default ledger file (whatever is read when you run `ledger`
without arguments), you should find that if you run ledger-autosync again, it
should print no transactions. This is because of the deduplicating feature: only
new transactions should be printed for insertion into your ledger files.

### Using the ofx protocol for automatic download

ledger-autosync also supports using the OFX protocol to automatically connect to
banks and download data. You can use the ofxclient program (which should have
been installed with ledger-autosync) to set up banking:

    $ ofxclient

When you have added your institution, quit ofxclient.

(At least one user has reported being signed up for a pay service by
setting up OFX direct connect. Although this seems unusual, please be
aware of this.)

Edit the generated `~/ofxclient.ini` file. Change the `description`
field of your accounts to the name used in ledger. Optionally, move the
`~/ofxclient.ini` file to your `~/.config` directory.

Run:

    ledger-autosync

This will download a maximum of 90 days previous activity from your
accounts. The output will be in ledger format and printed to stdout. Add
this output to your ledger file. When that is done, you can call:

    ledger-autosync

again, and it should print nothing to stdout, because you already have
those transactions in your ledger.

## Syncing a file

Some banks allow users to download OFX files, but do not support
fetching via the OFX protocol. If you have an OFX file, you can convert
to ledger:

    ledger-autosync /path/to/file.ofx

This will print unknown transactions in the file to stdout in the same
way as ordinary sync. If the transaction is already in your ledger, it
will be ignored.

## How it works

ledger-autosync stores a unique identifier, (for OFX files, this is a unique ID
provided by your institution for each transaction), as metadata in each
transaction. When syncing with your bank, it will check if the transaction
exists by running the ledger or hledger command. If the transaction exists, it
does nothing. If it does not exist, the transaction is printed to stdout.

## Syncing a CSV file

If you have a CSV file, you may also be able to import it using a recent
(installed via source) version of ledger-autosync. ledger-autosync can currently
process CSV files as provided by Paypal, Amazon, or Mint. You can process the
CSV file as follows:

    ledger-autosync /path/to/file.csv -a Assets:Paypal

With Amazon and Paypal CSV files, each row includes a unique identifier, so
ledger-autosync will be able to deduplicate against any previously imported
entries in your ledger files.

With Mint, a unique identifier based on the data in the row is generated and
stored. If future downloads contain identical rows, they will be deduplicated.
This method is probably not as robust as a method based on unique ids, but Mint
does not provide a unique id, and it should be better than nothing. It is likely
to generate false negatives: transactions that seem new, but are in fact old. It
will not generate false negatives: transactions that are not generated because
they seem old.

If you are a developer, you should fine it easy enough to add a new CSV format
to ledger-autosync. See, for example, the `MintConverter` class in the
`ledgerautosync/converter.py` file in this repository.

## Assertions

If you supply the `--assertions` flag, ledger-autosync will also print
out valid ledger assertions based on your bank balances at the time of
the sync. These otherwise empty transactions tell ledger that your
balance *should* be something at a given time, and if not, ledger will
fail with an error.

## 401k and investment accounts

If you have a 401k account, ledger-autosync can help you to track the state of
it. You will need OFX files (or an OFX protocol connection as set up by
ofxclient) provided by your 401k.

In general, your 401k account will consist of buy transactions, transfers and
reinvestments. The type will be printed in the payee line after a colon (`:`)

The buy transactions are your contributions to the 401k. These will be printed
as follows:

```
2016/01/29 401k: buymf
  ; ofxid: 1234
  Assets:Retirement:401k                                 1.12345 FOOBAR @ $123.123456
  Income:Salary                                            -$138.32
```

This means that you bought (contributed) $138.32 worth of FOOBAR (your
investment fund) at the price of $123.123456. The money to buy the investment
came from your income. In ledger-autosync, the `Assets:Retirement:401k` account
is the one specified using the `--account` command line, or configured in your
`ofxclient.ini`. The `Income:Salary` is specified by the `--unknown-account`
option.

If the transaction is a “transfer” transaction, this usually means either a fee
or a change in your investment option:

```
2014/06/30 401k: transfer: out
  ; ofxid: 1234
  Assets:Retirement:401k                                -1.61374 FOOBAR @ $123.123456
  Transfer                                                  $198.69
```

You will need to examine your statements to determine if this was a fee or a
real transfer back into your 401k.

Another type of transaction is a “reinvest” transaction:

```
2014/06/30 401k: reinvest
  ; ofxid: 1234
  Assets:Retirement:401k                                0.060702 FOOBAR @ $123.123456
  Income:Interest                                            -$7.47
```

This probably indicates a reinvestment of dividends. ledger-autosync will print
`Income:Interest` as the other account.

## resync

By default, ledger-autosync will process transactions backwards, and
stop when it sees a transaction that is already in ledger. To force it
to process all transactions up to the `--max` days back in time
(default: 90), use the `--resync` option. This can be useful when
increasing the `--max` option. For instance, if you previously
synchronized 90 days and now want to get 180 days of transactions,
ledger-autosync would stop before going back to 180 days without the
`--resync` option.

## Testing

ledger-autosync uses nose for tests. To test, run nosetests in the
project directory. This will test the ledger, hledger and ledger-python
interfaces. To test a single interface, use nosetests -a
hledger. To test the generic code, use nosetests -a generic. To test
both, use nosetests -a generic -a hledger. For some reason
nosetests -a '!hledger' will not work.

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
import distutils.spawn
import logging
import os
import re
import subprocess
from queue import Empty, Queue
from subprocess import PIPE, Popen
from threading import Thread

from ledgerautosync.converter import Converter

csv.register_dialect("ledger", delimiter=",", quoting=csv.QUOTE_ALL, escapechar="\\")


def mk_ledger(ledger_file):
    if Ledger.available():
        return Ledger(ledger_file)
    elif HLedger.available():
        return HLedger(ledger_file)
    elif LedgerPython.available():
        # string_read=True works around
        # http://bugs.ledger-cli.org/show_bug.cgi?id=973
        return LedgerPython(ledger_file, string_read=True)
    else:
        raise Exception("Neither ledger 3 nor hledger found!")


class MetaLedger(object):
    @staticmethod
    def windows_clean(a):
        def clean_str(s):
            s = s.replace("%", "")
            s = s.replace(" ", "\\ ")
            s = s.replace("/", "\\/")
            return s

        return [clean_str(s) for s in a]

    # Return True if this ledgerlike interface is available
    @staticmethod
    def available():
        return False

    def add_payee(self, payee, account):
        if payee not in self.payees:
            self.payees[payee] = []
        if account not in self.payees[payee]:
            self.payees[payee].append(account)

    def filter_accounts(self, accts, exclude):
        accts_filtered = [a for a in accts if a != exclude]
        if accts_filtered:
            return accts_filtered[-1]
        else:
            return None

    def get_account_by_payee(self, payee, exclude):
        self.load_payees()
        return self.filter_accounts(self.payees.get(payee, []), exclude)

    def __init__(self):
        self.payees = None


class Ledger(MetaLedger):
    @staticmethod
    def available():
        return (distutils.spawn.find_executable("ledger") is not None) and (
            Popen(
                ["ledger", "--version"], stdout=PIPE, universal_newlines=True
            ).communicate()[0]
        ).startswith("Ledger 3")

    def __init__(self, ledger_file=None, no_pipe=True):
        if distutils.spawn.find_executable("ledger") is None:
            raise Exception("ledger was not found in $PATH")
        self._item = ""

        def enqueue_output(out, queue):
            buff = ""
            while buff is not None:
                buff = out.read(1)
                if buff is not None:
                    self._item += buff
                if self._item.endswith("] "):  # prompt
                    queue.put(self._item[0:-2])
                    self._item = ""
            out.close()

        self.use_pipe = (os.name == "posix") and not (no_pipe)
        self.args = ["ledger", "--args-only"]
        if ledger_file is not None:
            self.args += ["-f", ledger_file]
        if self.use_pipe:
            self.p = Popen(
                self.args,
                bufsize=1,
                stdin=PIPE,
                stdout=PIPE,
                universal_newlines=True,
                close_fds=True,
            )
            self.q = Queue()
            self.t = Thread(target=enqueue_output, args=(self.p.stdout, self.q))
            self.t.daemon = True  # thread dies with the program
            self.t.start()
            # read output until prompt
            try:
                self.q.get(True, 5)
            except Empty:
                logging.error("Could not get prompt (]) from ledger!")
                logging.error("Received: %s" % (self._item))
                exit(1)
        super(Ledger, self).__init__()

    @staticmethod
    def pipe_quote(a):
        def quote(s):
            s = s.replace("/", "\\\\/")
            s = s.replace("%", "")
            if not (re.match(r"^\w+$", s)):
                s = '"%s"' % (s)
            return s

        return [quote(s) for s in a]

    def run(self, cmd):
        if self.use_pipe:
            self.p.stdin.write("csv ")
            self.p.stdin.write(" ".join(Ledger.pipe_quote(cmd)))
            self.p.stdin.write("\n")
            logging.debug(" ".join(Ledger.pipe_quote(cmd)))
            try:
                return csv.reader(self.q.get(True, 5), dialect="ledger")
            except Empty:
                logging.error("Could not get prompt from ledger!")
                exit(1)
        else:
            cmd = self.args + ["csv"] + cmd
            if os.name == "nt":
                cmd = MetaLedger.windows_clean(cmd)
            return csv.reader(
                subprocess.check_output(cmd, universal_newlines=True).splitlines(),
                dialect="ledger",
            )

    def check_transaction_by_id(self, key, value):
        q = ["-E", "meta", "%s=%s" % (key, Converter.clean_id(value))]
        try:
            next(self.run(q))
            return True
        except StopIteration:
            return False

    def load_payees(self):
        if self.payees is None:
            self.payees = {}
            r = self.run(["show", "--actual"])
            for line in r:
                self.add_payee(line[2], line[3])

    def get_autosync_payee(self, payee, account):
        q = [
            account,
            "--last",
            "1",
            "--format",
            "%(quoted(payee))\n",
            "--limit",
            'tag("AutosyncPayee") == "%s"' % (payee),
        ]
        r = self.run(q)
        try:
            return next(r)[0]
        except StopIteration:
            return payee


class LedgerPython(MetaLedger):
    @staticmethod
    def available():
        try:
            import ledger  # noqa: F401

            return True
        except ImportError:
            return False

    def __init__(self, ledger_file=None, string_read=True):
        # sanity check for ledger python interface
        try:
            import ledger
        except ImportError:
            raise Exception("Ledger python interface not found!")
        if ledger_file is None:
            # TODO - better loading
            raise Exception
        else:
            if string_read:
                self.session = ledger.Session()
                self.journal = self.session.read_journal_from_string(
                    open(ledger_file).read()
                )
            else:
                self.journal = ledger.read_journal(ledger_file)

        super(LedgerPython, self).__init__()

    def load_payees(self):
        if self.payees is None:
            self.payees = {}
            for xact in self.journal:
                for post in xact.posts():
                    self.add_payee(xact.payee, post.reported_account().fullname())

    def check_transaction_by_id(self, key, value):
        q = self.journal.query('-E meta %s="%s"' % (key, Converter.clean_id(value)))
        return len(q) > 0

    def get_autosync_payee(self, payee, account):
        logging.error("payee lookup not implemented for LedgerPython, using raw payee")
        return payee


class HLedger(MetaLedger):
    @staticmethod
    def available():
        return distutils.spawn.find_executable("hledger") is not None

    @staticmethod
    def quote(a):
        def quote_str(s):
            s = s.replace("(", "\\(")
            s = s.replace(")", "\\)")
            return s

        return [quote_str(s) for s in a]

    def __init__(self, ledger_file=None):
        if distutils.spawn.find_executable("hledger") is None:
            raise Exception("hledger was not found in $PATH")
        self.args = ["hledger"]
        if ledger_file is not None:
            self.args += ["-f", ledger_file]
        super(HLedger, self).__init__()

    def run(self, cmd):
        cmd = HLedger.quote(self.args + cmd)
        if os.name == "nt":
            cmd = MetaLedger.windows_clean(cmd)
        logging.debug(" ".join(cmd))
        return subprocess.check_output(cmd, universal_newlines=True)

    def check_transaction_by_id(self, key, value):
        cmd = ["reg", "tag:%s=%s" % (key, Converter.clean_id(value))]
        return self.run(cmd) != ""

    def load_payees(self):
        if self.payees is None:
            self.payees = {}
            cmd = ["reg", "-O", "csv", "--real"]
            r = csv.DictReader(self.run(cmd).splitlines())
            for line in r:
                self.add_payee(line["description"], line["account"])

    def get_autosync_payee(self, payee, account):
        logging.error("payee lookup not implemented for HLedger, using raw payee")
        return payee

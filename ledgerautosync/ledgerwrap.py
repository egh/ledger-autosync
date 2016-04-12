# Copyright (c) 2013, 2014 Erik Hetzner
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

from __future__ import absolute_import
import xml.etree.ElementTree as ET
import os
import re
import subprocess
from subprocess import Popen, PIPE
from threading import Thread
from Queue import Queue, Empty
from ledgerautosync.formatter import clean_ofx_id
import logging


def hledger_clean(a):
    def clean_str(s):
        s = s.replace('(', '\(')
        s = s.replace(')', '\)')
        return s
    return [clean_str(s) for s in a]


def pipe_clean(a):
    def clean_str(s):
        s = s.replace('/', '\\\\/')
        s = s.replace('%', '')
        if not(re.match(r"^\w+$", s)):
            s = "\"%s\"" % (s)
        return s
    return [clean_str(s) for s in a]


def windows_clean(a):
    def clean_str(s):
        s = s.replace('%', '')
        s = s.replace(' ', '\ ')
        s = s.replace('/', '\/')
        return s
    return [clean_str(s) for s in a]


def clean_payee(s):
    s = s.replace('%', '')
    s = s.replace('/', '\/')
    s = s.replace("'", "")
    return s


def all_or_none(seq):
    """Returns the first value of seq if all values of seq are equal, or \
returns None."""
    if len(seq) == 0:
        return None

    def f(x, y):
        if (x == y):
            return x
        else:
            return None
    return reduce(f, seq, seq[0])


def mk_ledger(ledger_file):
    try:
        import ledger
        return LedgerPython(ledger_file, string_read=False)
    except ImportError:
        if os.name == 'posix':
            if ((subprocess.call("which ledger > /dev/null", shell=True) == 0)
                and (Popen(["ledger", "--version"], stdout=PIPE).
                     communicate()[0]).startswith("Ledger 3")):
                return Ledger(ledger_file)
            elif subprocess.call("which hledger > /dev/null", shell=True) == 0:
                return HLedger(ledger_file)
            else:
                raise Exception("Neither ledger 3 nor hledger found!")
        else:
            # windows, I guess ... just assume ledger
            return Ledger(ledger_file)


class Ledger(object):
    def __init__(self, ledger_file=None, no_pipe=True):
        self._item = ""

        def enqueue_output(out, queue):
            buff = ""
            while (buff is not None):
                buff = out.read(1)
                if (buff is not None):
                    self._item += buff
                if self._item.endswith("] "):  # prompt
                    queue.put(self._item[0:-2])
                    self._item = ""
            out.close()
        self.use_pipe = (os.name == 'posix') and not(no_pipe)
        self.args = ["ledger"]
        if ledger_file is not None:
            self.args += ["-f", ledger_file]
        if self.use_pipe:
            self.p = Popen(self.args, bufsize=1, stdin=PIPE, stdout=PIPE,
                           close_fds=True)
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

    def run(self, cmd):
        if self.use_pipe:
            self.p.stdin.write("xml ")
            self.p.stdin.write(" ".join(pipe_clean(cmd)))
            self.p.stdin.write("\n")
            logging.debug(" ".join(pipe_clean(cmd)))
            try:
                return ET.fromstring(self.q.get(True, 5))
            except Empty:
                logging.error("Could not get prompt from ledger!")
                exit(1)
        else:
            cmd = self.args + ["xml"] + cmd
            if os.name == 'nt':
                cmd = windows_clean(cmd)
            return ET.fromstring(subprocess.check_output(cmd))

    def get_transaction(self, q):
        d = self.run(q).findall('.//transactions/transaction')
        if len(d) == 0:
            return None
        else:
            return d[0]

    def check_transaction_by_ofxid(self, ofxid):
        return (self.get_transaction(
            ["-E", "meta", "ofxid=%s" % (clean_ofx_id(ofxid))])
            is not None)

    def get_account_by_payee(self, payee, exclude):
        payee_regex = clean_payee(payee).replace("*", "\\\\*")
        try:
            txn = self.run(["--real", "payee", payee_regex])
            if txn is None:
                return None
            else:
                accts = [node.text for node in
                         txn.findall('.//transactions/transaction/postings/posting/account/name')]
                accts_filtered = [a for a in accts if a != exclude]
                if accts_filtered:
                    return accts_filtered[-1]
                else:
                    return None
        except:
            logging.error("Error checking --real payee for %s" %
                          (payee_regex))


class LedgerPython(object):
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
                    open(ledger_file).read())
            else:
                self.journal = ledger.read_journal(ledger_file)

    def check_transaction_by_ofxid(self, ofxid):
        q = self.journal.query("-E meta ofxid=\"%s\"" % (clean_ofx_id(ofxid)))
        return len(q) > 0

    def get_account_by_payee(self, payee, exclude):
        q = self.journal.query("--real payee '%s'" % (clean_payee(payee)))
        accts = [p.account for p in q]
        accts_filtered = [a for a in accts if a.fullname() != exclude]
        if accts_filtered:
            return str(accts_filtered[-1])
        else:
            return None


class HLedger(object):
    def __init__(self, ledger_file=None):
        self.args = ["hledger"]
        if ledger_file is not None:
            self.args += ["-f", ledger_file]

    def run(self, cmd):
        cmd = hledger_clean(self.args + cmd)
        if os.name == 'nt':
            cmd = windows_clean(cmd)
        logging.debug(" ".join(cmd))
        return subprocess.check_output(cmd)

    def check_transaction_by_ofxid(self, ofxid):
        cmd = ["reg", "tag:ofxid=%s" % (clean_ofx_id(ofxid))]
        return self.run(cmd) != ''

    def get_account_by_payee(self, payee, exclude):
        cmd = ["reg", "-w200", "desc:%s" % (payee)]
        lines = self.run(cmd).splitlines()
        accts = [l[92:172].strip() for l in lines]
        accts_filtered = [a for a in accts if a != exclude]
        if accts_filtered:
            return accts_filtered[-1]
        else:
            return None

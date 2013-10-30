import xml.etree.ElementTree as ET
import os
import re
import time
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
    return [ clean_str(s) for s in a ]

def pipe_clean(a):
    def clean_str(s):
        s = s.replace('/', '\\\\/')
        s = s.replace('%', '')
        if not(re.match(r"^\w+$", s)):
            s = "\"%s\""%(s)
        return s
    return [ clean_str(s) for s in a ]

def windows_clean(a):
    def clean_str(s):
        s = s.replace('%', '')
        s = s.replace(' ', '\ ')
        s = s.replace('/', '\/')
        return s
    return [ clean_str(s) for s in a ]

def all_or_none(seq):
    """Returns the first value of seq if all values of seq are equal, or returns None."""
    if len(seq) == 0: 
        return None
    def f(x,y):
        if (x == y): return x
        else: return None
    return reduce(f, seq, seq[0])

def mk_ledger(ledger_file=None):
    if os.name == 'posix':
        if ((subprocess.call("which ledger > /dev/null", shell=True) == 0) and
            (Popen(["ledger", "--version"], stdout=PIPE).communicate()[0]).startswith("Ledger 3")):
            return Ledger(ledger_file)
        elif subprocess.call("which hledger > /dev/null", shell=True) == 0:
            return HLedger(ledger_file)
        else:
            raise Exception("Neither ledger 3 nor hledger found!")
    else:
        # windows, I guess ... just assume ledger
        return Ledger(ledger_file)

class Ledger(object):
    def __init__(self, ledger_file=None, no_pipe=False):
        self._item = ""
        def enqueue_output(out, queue):
            buff = ""
            while (buff != None):
                buff = out.read(1)
                if (buff != None):
                    self._item += buff
                if self._item.endswith("] "): # prompt
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
            self.t.daemon = True # thread dies with the program
            self.t.start()
            # read output until prompt
            try:
                self.q.get(True, 5)
            except Empty:
                logging.error("Could not get prompt (]) from ledger!")
                logging.error("Received: %s"%(self._item))
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
        return (self.get_transaction(["-E", "meta", "ofxid=%s"%(clean_ofx_id(ofxid))]) != None)
        
    def get_account_by_payee(self, payee, exclude):
        txn = self.run(["--real", "payee", payee])
        if txn is None: return None
        else: 
            accts = [ node.text for node in txn.findall('.//transactions/transaction/postings/posting/account/name') ]
            return all_or_none([ a for a in accts if a != exclude ])

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
        cmd = ["reg", "tag:ofxid=%s"%(ofxid)]
        return self.run(cmd) != ''

    def get_account_by_payee(self, payee, exclude):
        cmd = ["reg", "desc:%s"%(payee)]
        lines = self.run(cmd).splitlines()
        accts = [ l[32:59].strip() for l in lines ]
        return all_or_none([ a for a in accts if a != exclude ])

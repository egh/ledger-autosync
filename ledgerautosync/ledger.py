import json
import sys
import time
from subprocess import Popen, PIPE
from threading import Thread
from Queue import Queue, Empty
from ledgerautosync.formatter import clean_ofx_id

def enqueue_output(out, queue):
    item = ""
    buff = ""
    while (buff != None):
        buff = out.read(1)
        if (buff != None):
            item += buff
        if item.endswith("] "): # prompt
            queue.put(item[0:-2])
            item = ""
    out.close()

class Ledger(object):
    def __init__(self, ledger_file=None):
        on_posix = 'posix' in sys.builtin_module_names
        args = ["ledger"]
        if ledger_file is not None:
            args += ["-f", ledger_file]
        self.p = Popen(args, bufsize=1, stdin=PIPE, stdout=PIPE,
                       close_fds=on_posix)
        self.q = Queue()
        self.t = Thread(target=enqueue_output, args=(self.p.stdout, self.q))
        self.t.daemon = True # thread dies with the program
        self.t.start()
        # read output until prompt
        self.q.get()

    def run(self, cmd):
        self.p.stdin.write("json %s\n"%(cmd))
        return json.loads(self.q.get())['ledger']

    def get_transaction(self, q):
        d = self.run("reg %s"%(q))
        if d['transactions'] == '':
            return None
        else:
            return d['transactions']

    def get_transaction_by_ofxid(self, ofxid):
        return self.get_transaction("meta ofxid='%s'"%(clean_ofx_id(ofxid)))

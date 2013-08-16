from ofxparse import OfxParser
from StringIO import StringIO

class Synchronizer(object):
    def __init__(self, ledger):
        self.ledger = ledger
    
    def is_txn_synced(self, txn):
        return (self.ledger.get_transaction("meta fid=%s"%(txn.id)) != None)
    
    def filter(self, txns):
        return [ txn for txn in txns if not(self.is_txn_synced(txn)) ]

    def get_new_txns(self, acct):
        days = 7
        last_txns_len = 0
        while (True):
            raw = StringIO(acct.download(days))
            ofx = OfxParser.parse(raw)
            txns = ofx.account.statement.transactions
            new_txns = self.filter(txns)
            if (last_txns_len == len(txns)):
                # not getting anything new; we have reached the beginning
                return new_txns
            elif (len(txns) > len(new_txns)):
                # got more txns than were new, we've reached a stopping point
                return new_txns
            else:
                # all new txns, increase how far back we go
                days = days * 2
                last_txns_len = len(txns)

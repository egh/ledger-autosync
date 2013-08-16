from ofxparse import OfxParser
from StringIO import StringIO
import logging

class Synchronizer(object):
    def __init__(self, ledger):
        self.ledger = ledger

    def is_txn_synced(self, acctid, txn):
        return (self.ledger.get_transaction("meta ofxid=%s.%s"%(acctid, txn.id)) != None)
    
    def filter(self, ofx):
        txns = ofx.account.statement.transactions
        acctid = ofx.account.account_id
        return [ txn for txn in txns if not(self.is_txn_synced(acctid, txn)) ]

    def get_new_txns(self, acct, min_days=None, max_days=999999):
        if min_days is not None:
            days = min_days
        elif (max_days < 7):
            days = max_days
        else:
            days = 7
        last_txns_len = 0
        while (True):
            logging.debug("Downloading %d days of transactions."%(days))
            raw = acct.download(days)
            ofx = OfxParser.parse(raw)
            txns = ofx.account.statement.transactions
            new_txns = self.filter(ofx)
            if (last_txns_len == len(txns)):
                # not getting anything new; we have reached the beginning
                return (ofx, new_txns)
            elif (len(txns) > len(new_txns)) or (max_days >= days):
                # got more txns than were new or hit max_days, we've reached a stopping point
                return (ofx, new_txns)
            else:
                # all new txns, increase how far back we go
                days = days * 2
                logging.debug("Increasing days ago to %d."%(days))
                if (days > max_days): days = max_days
                last_txns_len = len(txns)

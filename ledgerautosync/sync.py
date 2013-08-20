from ofxparse import OfxParser
from StringIO import StringIO
import logging

class Synchronizer(object):
    def __init__(self, ledger):
        self.ledger = ledger

    def parse_file(self, path, accountname=None):
        ofx = OfxParser.parse(file(path))
        return (ofx, self.filter(ofx))

    def is_txn_synced(self, acctid, txn):
        ofxid = "%s.%s"%(acctid, txn.id)
        return self.ledger.check_transaction_by_ofxid(ofxid)
    
    def filter(self, ofx):
        txns = ofx.account.statement.transactions
        acctid = ofx.account.account_id
        return [ txn for txn in txns if not(self.is_txn_synced(acctid, txn)) ]

    def get_new_txns(self, acct, max_days=999999, resync=False):
        if resync or (max_days < 7):
            days = max_days
        else:
            days = 7
        last_txns_len = 0
        while (True):
            logging.debug("Downloading %d days of transactions (max_days=%d)."%(days, max_days))
            raw = acct.download(days)
            ofx = OfxParser.parse(raw)
            txns = ofx.account.statement.transactions
            new_txns = self.filter(ofx)
            if ((len(txns) > 0) and (last_txns_len == len(txns))):
                # not getting more txns than last time; we have
                # reached the beginning
                logging.debug("Not getting more txns than last time, done.")
                return (ofx, new_txns)
            elif (len(txns) > len(new_txns)) or (days >= max_days):
                # got more txns than were new or hit max_days, we've
                # reached a stopping point
                if (days >= max_days):
                    logging.debug("Hit max days.")
                else:
                    logging.debug("Got some stale txns.")
                return (ofx, new_txns)
            else:
                # all txns were new, increase how far back we go
                days = days * 2
                if (days > max_days): days = max_days
                logging.debug("Increasing days ago to %d."%(days))
                last_txns_len = len(txns)

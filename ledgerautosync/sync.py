class Synchronizer(object):
    def __init__(self, ledger):
        self.ledger = ledger
    
    def is_transaction_synced(self, txn):
        return (self.ledger.get_transaction("meta fid=%s"%(txn.id)) != None)
    
    def sync(self, txns):
        return [ txn for txn in txns if not(self.is_transaction_synced(txn)) ]

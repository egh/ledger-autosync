import os
import os.path
from ofxparse import OfxParser
from ledgerautosync.ledger import Ledger
from ledgerautosync.sync import Synchronizer

from unittest import TestCase

class TestLedger(TestCase):
    def test_fresh_sync(self):
        ledger = Ledger("fixtures/empty.lgr")
        ofx = OfxParser.parse(file('fixtures/checking.ofx'))
        sync = Synchronizer(ledger)
        txns = ofx.account.statement.transactions
        self.assertEqual(sync.sync(txns), txns)

    def test_fully_synced(self):
        ledger = Ledger("fixtures/checking.lgr")
        ofx = OfxParser.parse(file('fixtures/checking.ofx'))
        sync = Synchronizer(ledger)
        txns = ofx.account.statement.transactions
        self.assertEqual(sync.sync(txns), [])

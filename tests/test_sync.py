import os
import os.path
from ofxparse import OfxParser
from ofxclient.config import OfxConfig
from ledgerautosync.ledger import Ledger
from ledgerautosync.sync import Synchronizer

from unittest import TestCase
from mock import Mock

class TestLedger(TestCase):
    def test_fresh_sync(self):
        ledger = Ledger("fixtures/empty.lgr")
        ofx = OfxParser.parse(file('fixtures/checking.ofx'))
        sync = Synchronizer(ledger)
        txns = ofx.account.statement.transactions
        self.assertEqual(sync.filter(txns), txns)

    def test_fully_synced(self):
        ledger = Ledger("fixtures/checking.lgr")
        ofx = OfxParser.parse(file('fixtures/checking.ofx'))
        sync = Synchronizer(ledger)
        txns = ofx.account.statement.transactions
        self.assertEqual(sync.filter(txns), [])

    def test_no_new_txns(self):
        ledger = Ledger("fixtures/checking.lgr")
        acct = Mock()
        acct.download = Mock(return_value=file('fixtures/checking.ofx').read())
        sync = Synchronizer(ledger)
        self.assertEqual(len(sync.get_new_txns(acct)), 0)
        
    def test_all_new_txns(self):
        ledger = Ledger("fixtures/empty.lgr")
        acct = Mock()
        acct.download = Mock(return_value=file('fixtures/checking.ofx').read())
        sync = Synchronizer(ledger)
        self.assertEqual(len(sync.get_new_txns(acct)), 3)
        
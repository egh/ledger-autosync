import os
import os.path
from ofxparse import OfxParser
from ofxclient.config import OfxConfig
from ledgerautosync.ledger import Ledger
from ledgerautosync.sync import Synchronizer

from unittest import TestCase
from mock import Mock

class TestSync(TestCase):
    def test_fresh_sync(self):
        ledger = Ledger("fixtures/empty.lgr")
        sync = Synchronizer(ledger)
        ofx = OfxParser.parse(file('fixtures/checking.ofx'))
        txns1 = ofx.account.statement.transactions
        txns2 = sync.filter(ofx)
        self.assertEqual(txns1, txns2)

    def test_fully_synced(self):
        ledger = Ledger("fixtures/checking.lgr")
        sync = Synchronizer(ledger)
        (ofx, txns) = sync.parse_file('fixtures/checking.ofx')
        self.assertEqual(txns, [])

    def test_no_new_txns(self):
        ledger = Ledger("fixtures/checking.lgr")
        acct = Mock()
        acct.download = Mock(return_value=file('fixtures/checking.ofx'))
        sync = Synchronizer(ledger)
        self.assertEqual(len(sync.get_new_txns(acct, 7, 7)[1]), 0)
        
    def test_all_new_txns(self):
        ledger = Ledger("fixtures/empty.lgr")
        acct = Mock()
        acct.download = Mock(return_value=file('fixtures/checking.ofx'))
        sync = Synchronizer(ledger)
        self.assertEqual(len(sync.get_new_txns(acct, 7, 7)[1]), 3)
        
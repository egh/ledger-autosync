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
        ledger = Ledger(os.path.join('fixtures', 'empty.lgr'))
        sync = Synchronizer(ledger)
        ofx = OfxParser.parse(file(os.path.join('fixtures', 'checking.ofx')))
        txns1 = ofx.account.statement.transactions
        txns2 = sync.filter(ofx)
        self.assertEqual(txns1, txns2)

    def test_fully_synced(self):
        ledger = Ledger(os.path.join('fixtures', 'checking.lgr'))
        sync = Synchronizer(ledger)
        (ofx, txns) = sync.parse_file(os.path.join('fixtures', 'checking.ofx'))
        self.assertEqual(txns, [])

    def test_partial_sync(self):
        ledger = Ledger(os.path.join('fixtures', 'checking-partial.lgr'))
        sync = Synchronizer(ledger)
        (ofx, txns) = sync.parse_file(os.path.join('fixtures', 'checking.ofx'))
        self.assertEqual(len(txns), 1)

    def test_no_new_txns(self):
        ledger = Ledger(os.path.join('fixtures', 'checking.lgr'))
        acct = Mock()
        acct.download = Mock(return_value=file(os.path.join('fixtures', 'checking.ofx')))
        sync = Synchronizer(ledger)
        self.assertEqual(len(sync.get_new_txns(acct, 7, 7)[1]), 0)
        
    def test_all_new_txns(self):
        ledger = Ledger(os.path.join('fixtures', 'empty.lgr'))
        acct = Mock()
        acct.download = Mock(return_value=file(os.path.join('fixtures', 'checking.ofx')))
        sync = Synchronizer(ledger)
        self.assertEqual(len(sync.get_new_txns(acct, 7, 7)[1]), 3)
        
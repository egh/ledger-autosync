import os
import os.path
from ledgerautosync.ledger import Ledger

from unittest import TestCase

class TestLedger(TestCase):
    def setUp(self):
        self.ledger = Ledger("fixtures/checking.lgr")
    
    def test_transaction(self):
        self.assertEqual(self.ledger.get_transaction_by_ofxid("1101.1452687~7.0000486")['metadata'], 
                         {u'pair': {u'string': u'1101.1452687~7.0000486', u'key': u'ofxid'}})

    def test_nonexistent_transaction(self):
        self.assertEqual(self.ledger.get_transaction_by_ofxid("FOO"), None)
    
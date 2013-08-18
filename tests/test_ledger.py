import os
import os.path
from ledgerautosync.ledger import Ledger

from unittest import TestCase

class TestLedger(TestCase):
    def setUp(self):
        self.ledger = Ledger("fixtures/checking.lgr")
    
    def test_transaction(self):
        txn = self.ledger.get_transaction_by_ofxid("1101.1452687~7.0000486")
        self.assertEqual(txn['transaction']['metadata'], 
                         {u'pair': {u'string': u'1101.1452687~7.0000486', u'key': u'ofxid'}})

#    def test_transaction_substring(self):
#        self.assertIsNone(self.ledger.get_transaction_by_ofxid("1452687~7"))

    def test_nonexistent_transaction(self):
        self.assertEqual(self.ledger.get_transaction_by_ofxid("FOO"), None)
    
    def test_transaction_by_payee(self):
        txn = self.ledger.get_transaction_by_payee("AUTOMATIC WITHDRAWAL, ELECTRIC BILL WEB(S )")
        self.assertEqual(txn['transaction']['note'],
                         ' ofxid: 1101.1452687~7.0000487')
                                                                                                             
    # broken in ledger
#    def test_multiple_transaction(self):
#        ledger = Ledger("fixtures/multiple.lgr")
#        txn = self.ledger.get_transaction_by_payee("Baz")
#        self.assertEqual(len(txn) > 1)

import os
import os.path
from ledgerautosync.ledger import Ledger

from unittest import TestCase

class TestLedger(TestCase):
    def setUp(self):
        self.ledger = Ledger("fixtures/checking.lgr")
        self.hledger = Ledger("fixtures/checking.lgr")
    
    def test_transaction(self):
        self.assertTrue(self.ledger.check_transaction_by_ofxid("1101.1452687~7.0000486"))
        self.assertTrue(self.hledger.check_transaction_by_ofxid("1101.1452687~7.0000486"))
        
#    def test_transaction_substring(self):
#        self.assertIsNone(self.ledger.get_transaction_by_ofxid("1452687~7"))

    def test_nonexistent_transaction(self):
        self.assertFalse(self.ledger.check_transaction_by_ofxid("FOO"))
    
    def test_get_account_by_payee(self):
        account = self.ledger.get_account_by_payee("AUTOMATIC WITHDRAWAL, ELECTRIC BILL WEB(S )")
        self.assertEqual(account, "Bar")
                                                                                                             
    # broken in ledger
#    def test_multiple_transaction(self):
#        ledger = Ledger("fixtures/multiple.lgr")
#        txn = self.ledger.get_transaction_by_payee("Baz")
#        self.assertEqual(len(txn) > 1)

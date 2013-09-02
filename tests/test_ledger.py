import os
import os.path
from ledgerautosync.ledger import Ledger, HLedger

from unittest import TestCase

class TestLedger(TestCase):
    def setUp(self):
        self.ledger = Ledger("fixtures/checking.lgr")
        self.hledger = HLedger("fixtures/checking.lgr")
        self.ledger_nopipe = Ledger("fixtures/checking.lgr", no_pipe=True)

    def test_transaction(self):
        self.assertTrue(self.ledger.check_transaction_by_ofxid("1101.1452687~7.0000486"))
        self.assertTrue(self.hledger.check_transaction_by_ofxid("1101.1452687~7.0000486"))
        self.assertTrue(self.ledger_nopipe.check_transaction_by_ofxid("1101.1452687~7.0000486"))
        
#    def test_transaction_substring(self):
#        self.assertIsNone(self.ledger.get_transaction_by_ofxid("1452687~7"))

    def test_nonexistent_transaction(self):
        self.assertFalse(self.ledger.check_transaction_by_ofxid("FOO"))
        self.assertFalse(self.hledger.check_transaction_by_ofxid("FOO"))
        self.assertFalse(self.ledger_nopipe.check_transaction_by_ofxid("FOO"))
    
    def test_get_account_by_payee(self):
        account = self.ledger.get_account_by_payee("AUTOMATIC WITHDRAWAL, ELECTRIC BILL WEB(S )", exclude="Assets:Foo")
        self.assertEqual(account, "Expenses:Bar")

        account = self.hledger.get_account_by_payee("AUTOMATIC WITHDRAWAL, ELECTRIC BILL WEB(S )", exclude="Assets:Foo")
        self.assertEqual(account, "Expenses:Bar")

    def test_get_ambiguous_account_by_payee(self):
        ledger = Ledger("fixtures/checking-dynamic-account.lgr")
        hledger = HLedger("fixtures/checking-dynamic-account.lgr")

        account = ledger.get_account_by_payee("Generic", exclude="Assets:Foo")
        self.assertEqual(account, None)

        account = hledger.get_account_by_payee("Generic", exclude="Assets:Foo")
        self.assertEqual(account, None)

        account = ledger.get_account_by_payee("Generic", exclude="Assets:Foo")
        self.assertEqual(account, None)
                                                                                                             
    # broken in ledger
#    def test_multiple_transaction(self):
#        ledger = Ledger("fixtures/multiple.lgr")
#        txn = self.ledger.get_transaction_by_payee("Baz")
#        self.assertEqual(len(txn) > 1)

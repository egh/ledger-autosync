import os
import os.path
from ledgerautosync.ledger import Ledger, HLedger

from unittest import TestCase

class TestLedger(TestCase):
    def setUp(self):
        self.ledgers = [Ledger("fixtures/checking.lgr"),
                        HLedger("fixtures/checking.lgr"),
                        Ledger("fixtures/checking.lgr", no_pipe=True)]
    def test_transaction(self):
        for ledger in self.ledgers:
            self.assertTrue(ledger.check_transaction_by_ofxid("1101.1452687~7.0000486"))
        
#    def test_transaction_substring(self):
#        self.assertIsNone(self.ledger.get_transaction_by_ofxid("1452687~7"))

    def test_nonexistent_transaction(self):
        for ledger in self.ledgers:
            self.assertFalse(ledger.check_transaction_by_ofxid("FOO"))
    
    def test_get_account_by_payee(self):
        for ledger in self.ledgers:
            account = ledger.get_account_by_payee("AUTOMATIC WITHDRAWAL, ELECTRIC BILL WEB(S )", exclude="Assets:Foo")
            self.assertEqual(account, "Expenses:Bar", msg="%s != Expenses:Bar with %s"%(account, ledger))

    def test_get_ambiguous_account_by_payee(self):
        ledgers = [Ledger("fixtures/checking-dynamic-account.lgr"),
                   Ledger("fixtures/checking-dynamic-account.lgr", no_pipe=True),
                   HLedger("fixtures/checking-dynamic-account.lgr")]
        
        for ledger in ledgers:
            account = ledger.get_account_by_payee("Generic", exclude="Assets:Foo")
            self.assertEqual(account, None)
                                                                                                             
    # broken in ledger
#    def test_multiple_transaction(self):
#        ledger = Ledger("fixtures/multiple.lgr")
#        txn = self.ledger.get_transaction_by_payee("Baz")
#        self.assertEqual(len(txn) > 1)

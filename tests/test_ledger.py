from __future__ import absolute_import
import os
import os.path
from ledgerautosync.ledgerwrap import Ledger, HLedger, LedgerPython

from unittest import TestCase
import ledger

class TestLedger(TestCase):
    def setUp(self):
        self.ledgers = [LedgerPython(os.path.join('fixtures', 'checking.lgr')),
                        HLedger(os.path.join('fixtures', 'checking.lgr')),
                        Ledger(os.path.join('fixtures', 'checking.lgr'), no_pipe=True)]

    def test_transaction(self):
        for lgr in self.ledgers:
            self.assertTrue(lgr.check_transaction_by_ofxid("1101.1452687~7.0000486"))
        
#    def test_transaction_substring(self):
#        self.assertIsNone(lgr.get_transaction_by_ofxid("1452687~7"))

    def test_nonexistent_transaction(self):
        for lgr in self.ledgers:
            self.assertFalse(lgr.check_transaction_by_ofxid("FOO"))

    def test_empty_transaction(self):
        for lgr in self.ledgers:
            self.assertTrue(lgr.check_transaction_by_ofxid("empty"))
    
    def test_get_account_by_payee(self):
        for lgr in self.ledgers:
            account = lgr.get_account_by_payee("AUTOMATIC WITHDRAWAL, ELECTRIC BILL WEB(S )", exclude="Assets:Foo")
            self.assertEqual(account, "Expenses:Bar", msg="%s != Expenses:Bar with %s"%(account, lgr))

    def test_get_ambiguous_account_by_payee(self):
        ledgers = [LedgerPython(os.path.join('fixtures', 'checking-dynamic-account.lgr')),
                   Ledger(os.path.join('fixtures', 'checking-dynamic-account.lgr'), no_pipe=True),
                   HLedger(os.path.join('fixtures', 'checking-dynamic-account.lgr'))]
        
        for lgr in ledgers:
            account = lgr.get_account_by_payee("Generic", exclude="Assets:Foo")
            # shoud use the latest
            self.assertEqual(account, "Expenses:Bar")
                                                                                                             
    # broken in ledger
#    def test_multiple_transaction(self):
#        lgr = Ledger("fixtures/multiple.lgr")
#        txn = lgr.get_transaction_by_payee("Baz")
#        self.assertEqual(len(txn) > 1)

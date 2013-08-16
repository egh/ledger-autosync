import ledgerautosync.formatter

from ofxparse import OfxParser

from unittest import TestCase
from mock import Mock

class TestGenerate(TestCase):
    def setUp(self):
        self.ofx = OfxParser.parse(file('fixtures/checking.ofx'))

    def testIt(self):
        formatter = ledgerautosync.formatter.Formatter(acctid=self.ofx.account.account_id, currency=self.ofx.account.statement.currency, name="Foo")
        self.assertEqual(formatter.format_txn(self.ofx.account.statement.transactions[0]),
"""2011/03/31 DIVIDEND EARNED FOR PERIOD OF 03/01/2011 THROUGH 03/31/2011 ANNUAL PERCENTAGE YIELD EARNED IS 0.05%
  ; fid: 1452687~7.0000486
  Foo  $0.01
  Expenses:Misc  -$0.01
""")
        self.assertEqual(formatter.format_txn(self.ofx.account.statement.transactions[1]),
"""2011/04/05 AUTOMATIC WITHDRAWAL, ELECTRIC BILL WEB(S )
  ; fid: 1452687~7.0000487
  Foo  -$34.51
  Expenses:Misc  $34.51
""")
        self.assertEqual(formatter.format_txn(self.ofx.account.statement.transactions[2]),
"""2011/04/07 RETURNED CHECK FEE, CHECK # 319 FOR $45.33 ON 04/07/11
  ; fid: 1452687~7.0000488
  Foo  -$25.00
  Expenses:Misc  $25.00
""")

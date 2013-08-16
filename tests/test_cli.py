from ledgerautosync.cli import run
from ledgerautosync.ledger import Ledger
from ofxclient.config import OfxConfig

from unittest import TestCase
from mock import Mock

class TestCli(TestCase):
    def test_run(self):
        ledger = Ledger('fixtures/empty.lgr')
        config = OfxConfig('fixtures/ofxclient.ini')
        acct = config.accounts()[0]
        acct.download = Mock(return_value=file('fixtures/checking.ofx'))
        config.accounts = Mock(return_value=[acct])
        run(ledger, config, 7, 7)

    def test_empty_run(self):
        ledger = Ledger('fixtures/checking.lgr')
        config = OfxConfig('fixtures/ofxclient.ini')
        acct = config.accounts()[0]
        acct.download = Mock(return_value=file('fixtures/checking.ofx'))
        config.accounts = Mock(return_value=[acct])
        run(ledger, config, 7, 7)

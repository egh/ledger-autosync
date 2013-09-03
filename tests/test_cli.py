from ledgerautosync.cli import sync
from ledgerautosync.ledger import Ledger
from ofxclient.config import OfxConfig
import os.path

from unittest import TestCase
from mock import Mock

class TestCli(TestCase):
    def test_run(self):
        ledger = Ledger(os.path.join('fixtures', 'empty.lgr'))
        config = OfxConfig(os.path.join('fixtures', 'ofxclient.ini'))
        acct = config.accounts()[0]
        acct.download = Mock(return_value=file(os.path.join('fixtures', 'checking.ofx')))
        config.accounts = Mock(return_value=[acct])
        sync(ledger, config, 7)

    def test_empty_run(self):
        ledger = Ledger(os.path.join('fixtures', 'checking.lgr'))
        config = OfxConfig(os.path.join('fixtures', 'ofxclient.ini'))
        acct = config.accounts()[0]
        acct.download = Mock(return_value=file(os.path.join('fixtures', 'checking.ofx')))
        config.accounts = Mock(return_value=[acct])
        sync(ledger, config, 7)

from __future__ import absolute_import
from ledgerautosync.cli import import_ofx
from ledgerautosync.ledger import Ledger
from ledgerautosync import EmptyInstitutionException
import os.path

from unittest import TestCase
from mock import Mock
from nose.tools import raises

class TestCli(TestCase):

    @raises(EmptyInstitutionException)
    def test_no_institution_no_fid(self):
        ledger = Ledger(os.path.join('fixtures', 'empty.lgr'))
        ofxpath = os.path.join('fixtures', 'no-institution.ofx')
        import_ofx(ledger, ofxpath, accountname="Assets:Foo")

    def test_no_institution(self):
        ledger = Ledger(os.path.join('fixtures', 'empty.lgr'))
        ofxpath = os.path.join('fixtures', 'no-institution.ofx')
        import_ofx(ledger, ofxpath, accountname="Assets:Foo", fid=1234567890)

    @raises(EmptyInstitutionException)
    def test_no_institution_no_accountname(self):
        ledger = Ledger(os.path.join('fixtures', 'empty.lgr'))
        ofxpath = os.path.join('fixtures', 'no-institution.ofx')
        import_ofx(ledger, ofxpath, fid=1234567890)

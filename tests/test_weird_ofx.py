# Copyright (c) 2013, 2014 Erik Hetzner
# 
# This file is part of ledger-autosync
#
# ledger-autosync is free software: you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# ledger-autosync is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with ledger-autosync. If not, see
# <http://www.gnu.org/licenses/>.

from __future__ import absolute_import
from ledgerautosync.cli import import_ofx
from ledgerautosync.ledgerwrap import Ledger
from ledgerautosync import EmptyInstitutionException
import os.path

from unittest import TestCase
from mock import Mock
from nose.tools import raises

class TestCli(TestCase):

    @raises(EmptyInstitutionException)
    def test_no_institution_no_fid(self):
        lgr = Ledger(os.path.join('fixtures', 'empty.lgr'))
        ofxpath = os.path.join('fixtures', 'no-institution.ofx')
        import_ofx(lgr, ofxpath, accountname="Assets:Foo")

    def test_no_institution(self):
        lgr = Ledger(os.path.join('fixtures', 'empty.lgr'))
        ofxpath = os.path.join('fixtures', 'no-institution.ofx')
        import_ofx(lgr, ofxpath, accountname="Assets:Foo", fid=1234567890)

    @raises(EmptyInstitutionException)
    def test_no_institution_no_accountname(self):
        lgr = Ledger(os.path.join('fixtures', 'empty.lgr'))
        ofxpath = os.path.join('fixtures', 'no-institution.ofx')
        import_ofx(lgr, ofxpath, fid=1234567890)

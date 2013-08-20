from decimal import Decimal
from ofxparse.ofxparse import Transaction, InvestmentTransaction

def clean_ofx_id(ofxid):
    ofxid = ofxid.replace('/', '_')
    ofxid = ofxid.replace('$', '_')
    ofxid = ofxid.replace(' ', '_')
    return ofxid

class Formatter(object):
    def __init__(self, account, name, ledger=None):
        self.acctid=account.account_id
        self.currency=account.statement.currency
        self.fid=account.institution.fid
        self.name = name
        self.ledger = ledger

    def mk_dynamic_account(self, txn):
        if self.ledger is None:
            return "Expenses:Misc"
        else:
            payee = self.format_payee(txn)
            account = self.ledger.get_account_by_payee(payee)
            if account is None:
                return "Expenses:Misc"
            else:
                return account

    def format_amount(self, amount, reverse=False, unlimited=False):
        currency = self.currency.upper()
        if currency == "USD": currency = "$"
        if unlimited:
            amt = str(abs(amount))
        else:
            amt = "%0.2f"%(abs(amount))
        if amount.is_signed() != reverse:
            return "-%s%s"%(currency, amt)
        else:
            return "%s%s"%(currency, amt)

    def format_payee(self, txn):
        if (txn.payee is None) or txn.memo.startswith(txn.payee):
            return txn.memo
        elif (txn.memo is None) or txn.payee.startswith(txn.memo):
            return txn.payee
        else:
            return "%s %s"%(txn.payee, txn.memo)

    def format_txn_line(self, acct, amt, extra=None):
        space_count = 50 - len(acct) - len(amt)
        if extra:
            extra_str = " %s"%(extra)
        else:
            extra_str = ""
        return "  %s%s%s%s\n"%(acct, (" " * space_count), amt, extra_str)

    def format_txn(self, txn):
        retval = ""
        ofxid = clean_ofx_id("%s.%s.%s"%(self.fid, self.acctid, txn.id))
        if isinstance(txn, Transaction):
            date = "%s"%(txn.date.strftime("%Y/%m/%d"))
            retval += "%s %s\n"%(date, self.format_payee(txn))
            retval += "  ; ofxid: %s\n"%(ofxid)
            retval += self.format_txn_line(self.name, self.format_amount(txn.amount))
            retval += self.format_txn_line(self.mk_dynamic_account(txn), self.format_amount(txn.amount, reverse=True))
        elif isinstance(txn, InvestmentTransaction):
            trade_date = "%s"%(txn.tradeDate.strftime("%Y/%m/%d"))
            if txn.settleDate is not None:
                retval = "%s=%s %s\n"%(txn.tradeDate.strftime("%Y/%m/%d"), txn.settleDate.strftime("%Y/%m/%d"), txn.memo)
            else:
                retval = "%s %s\n"%(txn.tradeDate.strftime("%Y/%m/%d"), txn.memo)
            retval += "  ; ofxid: %s\n"%(ofxid)
            retval += self.format_txn_line(self.name, str(txn.units), 
                                           "%s @ %s"%(txn.security, self.format_amount(txn.unit_price, unlimited=True)))
            retval += self.format_txn_line(self.name, self.format_amount(txn.units * txn.unit_price, reverse=True))
        return retval

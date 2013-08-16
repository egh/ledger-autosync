from decimal import Decimal
from ofxparse.ofxparse import Transaction, InvestmentTransaction
class Formatter(object):
    def __init__(self, acctid, currency, name):
        self.currency = currency
        self.name = name
        self.acctid = acctid

    def mk_dynamic_account(self, txn):
        return "Expenses:Misc"
    
    def format_amount(self, amount, reverse=False):
        currency = self.currency.upper()
        if currency == "USD": currency = "$"
        amt = "%0.2f"%(abs(amount))
        if amount.is_signed() != reverse:
            return "-%s%s"%(currency, amt)
        else:
            return "%s%s"%(currency, amt)

    def format_txn(self, txn):
        retval = ""
        if isinstance(txn, Transaction):
            date = "%s"%(txn.date.strftime("%Y/%m/%d"))
            retval += "%s %s\n"%(date, txn.memo)
            retval += "  ; ofxid: %s.%s\n"%(self.acctid, txn.id)
            retval += "  %s  %s\n"%(self.name, self.format_amount(txn.amount))
            retval += "  %s  %s\n"%(self.mk_dynamic_account(txn), self.format_amount(txn.amount, True))
        elif isinstance(txn, InvestmentTransaction):
            trade_date = "%s"%(txn.tradeDate.strftime("%Y/%m/%d"))
            if txn.settleDate is not None:
                retval = "%s=%s %s\n"%(txn.tradeDate, txn.settleDate.strftime("%Y/%m/%d"), txn.memo)
            else:
                retval = "%s %s\n"%(txn.tradeDate, txn.memo)
            retval += "  ; ofxid: %s.%s\n"%(self.acctid, txn.id)
            retval += "  %s  %s %s @ %s\n"%(self.name, txn.units, txn.security, txn.unit_price)
            retval += "  %s  %s\n"%(self.name, self.format_amount(txn.units * txn.unit_price, True))
        return retval

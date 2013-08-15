from decimal import Decimal

class Formatter(object):
    def __init__(self, acct):
        self.account = acct

    def mk_fixed_account(self):
        return "Foo"
        
    def mk_dynamic_account(self, txn):
        return "Bar"
    
    def format_amount(self, txn, reverse=False):
        currency = self.account.statement.currency.upper()
        if currency == "USD": currency = "$"
        if txn.amount.is_signed() != reverse:
            return "-%s%s"%(currency, str(abs(txn.amount)))
        else:
            return "%s%s"%(currency, str(abs(txn.amount)))
            
    def format_txn(self, txn):
        date = "%s"%(txn.date.strftime("%Y/%m/%d"))
        retval = "%s %s\n"%(date, txn.memo)
        retval += "  ; fid: %s\n"%(txn.id)
        retval += "  %s  %s\n"%(self.mk_fixed_account(), self.format_amount(txn))
        retval += "  %s  %s\n"%(self.mk_dynamic_account(txn), self.format_amount(txn, True))
        return retval

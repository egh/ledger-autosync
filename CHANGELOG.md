## Unreleased
- Migrated to python3
- Add --reverse option to print txns in reverse
- Better error handling on OFX server error
- Add --shorten-account, --hardcode-account options
  improve user privacy
- Add --payee-format argument
- Move ofxid metadata to correct posting
- Misc bugfixes

## Version 0.3.5
- Disable default usage of python bindings
- Change to using 65 spaces to align txns (per ledger-mode)
- Improve .ledgerrc parsing
- Better error messages
- Add basic plugin system
- Misc bugfixes

## Version 0.3.4
- Packaging fixes
  
## Version 0.3.3
- Fix problem building on ubuntu trusty

## Version 0.3.2
- Fix problem with certain characters in transaction id

## Version 0.3.0
- Support CSV files (Mint, Paypal and Amazon flavors)
- Uses ticker symbol by for currencies, not CUSIP (You will need to change
  previous transactions which used the CUSIP so they work with new transactions)
- Dividends will now be formatted correctly
- Fuzzy payee matching

## Version 0.2.5
- Support advanced investment transactions
- Upgrade to ofxparse 0.15

## Version 0.2.4
- Add `--unknown-account` argument

## Version 0.2.2
- Better support for strange OFX, payee characters

## Version 0.2.1
- Support ledger python API

## Version 0.2.0
- Improved hledger support

## Version 0.1.4
- Balance assertions
- Initial balance

## Version 0.1.3
- Reverse transactions

## Version 0.1.0
- Initial release

#!/usr/bin/python
import re
import sys

first_line = False
ofxline = None

with open(sys.argv[1]) as f:
    for line in f.readlines():
        md = re.match(r"^(19|20)[0-9][0-9]", line)
        if md is not None:
            # Mark the next line as the first line in a txn
            first_line = True
        else:
            if first_line:
                first_line = False
                # Check if there is an ofxid on this line
                md = re.match(r"^\s+; ofxid:", line)
                if md is not None:
                    ofxline = line
                    continue
        # In every case except the one above where we call next, print the line
        sys.stdout.write(line)
        # We had a misplaced ofxid last, print it now
        if ofxline:
            sys.stdout.write(ofxline)
            ofxline = None

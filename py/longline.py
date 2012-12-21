#!/usr/bin/python

import sys
from optparse import OptionParser

def read_options():
    usage = "%prog"
    parser = OptionParser(usage)
    parser.add_option("-f", "--file", dest="inputfile", help="the downloaded html source")
    parser.add_option("-l", "--bylength", dest="sortbylength", default=False, action="store_true", help="sort by line length ascending")
    (op, args) = parser.parse_args()
    if not op.inputfile:
        parser.error("missing required option; -h for help")
    return op

if __name__ == "__main__":
    
    op = read_options()
    f = open(op.inputfile, "r")
    
    data = f.readlines()
    
    by_length = {}
    
    i = 0
    longest_len = 0
    longest_line = 0
    longest_content = None
    for lyne in data:
        i += 1
        current_len = len(lyne)
        lynes = by_length.get(current_len, [])
        lynes.append(lyne)
        by_length[current_len] = lynes
        
        if (current_len > longest_len):
            longest_len = current_len
            longest_line = i
            longest_content = lyne
        if not op.sortbylength:
            print("#%s (%s)" % (i, current_len))
            
    if op.sortbylength:
        i = 0
        for lyne_length in sorted(by_length.keys()):
            for lyne in by_length.get(lyne_length):
                i += 1
                print("(%d) %s%s" % (lyne_length, lyne[:80], (len(lyne) > 80) and "..." or ""))
                
    if not op.sortbylength:
        print
        print("Longest line: #%s (%s):\n %s" % (longest_line, longest_len, longest_content))
    f.close()
    
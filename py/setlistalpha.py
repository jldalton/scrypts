#!/usr/bin/python

from urllib import urlopen
from optparse import OptionParser

"""
Extracts the songs from a setlist.fm page
and displays them in alphabetical order

USAGE EXAMPLE:
python setlistalpha.py -u http://www.setlist.fm/setlist/rush/2010/superpagescom-center-dallas-tx-1bd5c1b8.html
"""

if __name__ == "__main__":
    
    version = "1.0"
    usage = "%prog [options]\n" + \
            "Version " + version + "\n"
    parser = OptionParser(usage)
    parser.add_option("-f", "--file", dest="inputfile", help="the html file")
    parser.add_option("-u", "--url", dest="inputurl", help="the url of the html")
    (op, args) = parser.parse_args()
    
    if not op.inputfile:
        if not op.inputurl:
            print "URL?"
            url = raw_input()
        else:
            url = op.inputurl
        data = urlopen(url).read()
    else:
        f = file(op.inputfile,"r")
        data = f.read()
        
    songs = set()
    for row in data.split('\n'):
        if 'a class="song' in row:
            song_title = row[1+row.index(">"):row.index("<",2)]
            songs.add(song_title)
    
    for song in sorted(songs):
        print('%s' % song)
        
    print('\nTotal:%d' % len(songs)) 
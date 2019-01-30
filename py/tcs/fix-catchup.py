import sys

-- simple data transform to replace the 1st element and null out the 8th

if len(sys.argv) < 2:
    print("filename?")

fn = sys.argv[1]

with open('map.txt') as f:
    mapping = [r.strip() for r in f.readlines()]

xref = {}
for m in mapping:
    a = m.split('|')
    xref[a[0]] = a[1]

header = True
with open(fn) as f:
    lines = [r.strip() for r in f.readlines()]

for r in lines:
    if header:
        print r
    else:
        r1 = r.split('|')
        k = r1[0]
        v = xref[k]
        r1[1] = v
        r1[8] = ''
        print("|".join(r1))
    header = False

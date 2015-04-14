import sys

if len(sys.argv) < 2:
    print("Usage: %s {consolidated-output-file}" % sys.argv[0])
    sys.exit()

ok = 0
ill = 0
blk = 0
missing = 0
other = 0
total = 0

with open(sys.argv[1]) as f:
    for ln in f.readlines():
        total += 1
        if "OK,ok" in ln:
            ok += 1
        if "NO-EMAIL" in ln:
            missing += 1
        if "err:" in ln:
            if "email:blocked" in ln:
                blk += 1
            elif "email:illegal" in ln:
                ill += 1
            else:
                print(ln)
                other += 1


print("Total reminder emails scheduled: %s" % total)
print("Total successfully emailed: %s" % ok)
print("Total blocked: %s" % blk)
print("Total illegal: %s" % ill)
print("Total without email: %s" % missing)
if other > 0:
    print("Other: %s" % other)

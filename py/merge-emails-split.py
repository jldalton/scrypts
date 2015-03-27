import sys

"""
this splits a file of the format:

11100002142680,C,alma simmons,a.simmons@madeupemail.net,5558675309|5558675301
11100001337661,C,anthony simmons,a.simmons@madeupemail.net,5558675309
11100003154979,C,andrew walzer,a.walzer@madeupemail.com,5558675309
11100003245031,C,annette walzer,a.walzer@madeupemail.com,5558675309

into several chunks of a relatively fixed size, but keeps
records with the same email addresses in the same chunk
"""

def email_of(lyne):
    return lyne.split(",")[3]

def split(args):
    if len(args) < 4:
        print("Usage:\npython %s {filename} {chunk_size} {prefix} [{ext}]" % args[0])
        sys.exit()

    filename = args[1]
    chunk_size = int(args[2])
    prefix = args[3]
    if len(args) == 5:
        ext = args[4]
    else:
        ext = None
    chunk_count = 0
    with open(filename) as f:
        chunk = []
        all_lines = [ln.strip() for ln in f.readlines()]
        while len(all_lines) > 0:
            if len(all_lines) <= chunk_size:
                n = len(all_lines)
            else:
                n = chunk_size
                while n < len(all_lines) and email_of(all_lines[n]) == email_of(all_lines[n-1]):
                    n += 1

            chunk_count += 1
            chunk_fn = "%s%s.%s" % (prefix, chunk_count, ext or "")
            with open(chunk_fn, 'w') as fc:
                for outline in all_lines[0:n]:
                    fc.write("%s\n" % outline)
            print(chunk_fn)

            all_lines = all_lines[n:]


if __name__ == "__main__":
    split(sys.argv)

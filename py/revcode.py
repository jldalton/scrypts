#!/usr/bin/env python

import math
import sys

"""
Reversible Codes

Ported from Nik's http://jsfiddle.net/nikb747/muS2P/
"""

BIG_ALPHABET = 'BCDEFGHJKMNPRSTVWXY23456789!@#$%^&*()-_+abcdefghijklmnopqrstuvxywz'

ALPHABET = 'BCDEFGHJKMNPRSTVWXY23456789' # 'ABCDEFGHJKMNPRSTUVWXY23456789'


#ALPHABET = 'CDEFHJKMNPRVWXY23456789'
NUM_CHARS = len(ALPHABET)
STORE_SIZE = 3
SHIFT_INDEX = 3
SEQUENCE_SIZE = 8
MOD_BY = 23

verbose = True

def encode_store_and_sequence(store, sequence):
    shift = sequence % MOD_BY + 1
    return "%s%s%s" % ( encode(store, STORE_SIZE, shift), ALPHABET[shift], encode(sequence, SEQUENCE_SIZE, shift) )

def decode_to_store_and_sequence(enc):
    c = enc[SHIFT_INDEX]
    shift = ALPHABET.index(c)
    store = decode(enc[0:STORE_SIZE], shift)
    sequence = decode(enc[SHIFT_INDEX+1:], shift)
    return (store, sequence)

def encode(num, pad, shift):
    constructed = ""
    digits = ((int(math.floor(num / NUM_CHARS ** power)) % NUM_CHARS + shift + power)
              % NUM_CHARS for power in range(0,pad))
    base_digits = [x for x in digits]
    num_base_digits = len(base_digits)
    for i in range(0, num_base_digits):
        shifted_index = (shift + i) % num_base_digits
        constructed = "%s%s" % (ALPHABET[base_digits[shifted_index]], constructed)
    return constructed

def decode(shifted_string, shift):
    repositioned_chars = {}
    total = 0
    l = len(shifted_string)
    for i in range(0, l):
        unshifted = wrap_to_positive(i - shift, l)
        repositioned_chars[unshifted] = shifted_string[i]
    num_repo_chars = len(repositioned_chars)
    for i in reversed(range(0, num_repo_chars)):
        power = num_repo_chars - i - 1
        some_digit = wrap_to_positive(ALPHABET.index(repositioned_chars[i]) - shift - power, NUM_CHARS)
        total += some_digit * NUM_CHARS ** power
    return int(total)

def wrap_to_positive(num_to_wrap, mod_by):
    wrap = num_to_wrap
    while wrap < 0 and mod_by > 0:
        wrap += mod_by
    return wrap % mod_by



args = sys.argv
store_start = int(args[1])
store_end = int(args[2])
seq_start = int(args[3])
seq_end = int(args[4])

count = 0
for store in range(store_start, store_end):
    for sequence in range(seq_start, seq_end):
        encoded = encode_store_and_sequence(store, sequence)
        if verbose:
            print(encoded)
        (dstore, dsequence) = decode_to_store_and_sequence(encoded)
        status = "OK" if dstore == store and dsequence == sequence else "ERROR"
        output = "%s => %s => [ %s | %s ] [%s]" % (sequence, encoded, dstore, dsequence, status)
        if status == "ERROR":
            msg = "hmm %s,%s <> %s,%s\n" % (store, sequence, dstore, dsequence)
            print(msg)
            sys.stderr.write(msg)
        count += 1
        if count % 100000 == 0:
            print(output)
            sys.stderr.write("%s %s %s %s\n" % (count, store, sequence, encoded))

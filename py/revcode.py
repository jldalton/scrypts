#!/usr/bin/env python

import math

"""
Reversible Codes

Ported from Nik's http://jsfiddle.net/nikb747/muS2P/
"""

ALPHABET = 'BCDEFGHJKMNPQRSTVWXYZ23456789'
NUM_CHARS = len(ALPHABET)
STORE_SIZE = 4
SHIFT_INDEX = 4
SEQUENCE_SIZE = 8
MOD_BY = 17

def encode_store_and_sequence(store, sequence):
    shift = sequence % MOD_BY + 1
    return "%s%s%s" % ( encode(store, STORE_SIZE, shift), ALPHABET[shift], encode(sequence, SEQUENCE_SIZE, shift) )

def decode_to_store_and_sequence(enc):
    c = enc[SHIFT_INDEX]
    shift = ALPHABET.index(c)
    store = decode(enc[0:4], shift)
    sequence = decode(enc[5:], shift)
    return (store, sequence)

def encode(num, pad, shift):
    base_digits = []
    constructed = []
    for power in range(0, pad):
        digit = int(math.floor(num / math.pow(NUM_CHARS, power))) % NUM_CHARS
        base_digits.append((digit + shift + power) % NUM_CHARS)
    for i in range(0, len(base_digits)):
        shifted_index = (shift + i) % len(base_digits)
        constructed.append(ALPHABET[base_digits[shifted_index]])
    return "".join(constructed[::-1])

def decode(shifted_string, shift):
    repos = {}
    total = 0
    for i in range(0, len(shifted_string)):
        unshifted = wrap_to_positive(i - shift, len(shifted_string))
        repos[unshifted] = shifted_string[i]
    for i in range(len(repos)-1, 0, -1):
        power = len(repos) - i - 1
        some_digit = wrap_to_positive(ALPHABET.index(repos[i]) - shift - power, NUM_CHARS)
        total += int(some_digit * math.pow(NUM_CHARS, power))
    return total

def wrap_to_positive(num_to_wrap, mod_by):
    wrap = num_to_wrap
    while wrap < 0 and mod_by > 0:
        wrap += mod_by
    return wrap % mod_by

for store in range(20, 25):
    for sequence in range(2000, 2100):
        encoded = encode_store_and_sequence(store, sequence)
        (dstore, dsequence) = decode_to_store_and_sequence(encoded)
        output = "%s => %s => [ %s | %s ]" % (sequence, encoded, dstore, dsequence)
        print(output)

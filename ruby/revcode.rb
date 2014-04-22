#!/usr/bin/env ruby

"""
Reversible Codes

Ported from Nik's http://jsfiddle.net/nikb747/muS2P/
"""

ALPHABET = 'BCDEFGHJKMNPQRSTVWXYZ23456789'
NUM_CHARS = ALPHABET.length
STORE_SIZE = 4
SHIFT_INDEX = 4
SEQUENCE_SIZE = 8
MOD_BY = 17

def encode_store_and_sequence(store, sequence)
    shift = sequence % MOD_BY + 1
    "#{encode(store, STORE_SIZE, shift)}#{ALPHABET[shift]}#{encode(sequence, SEQUENCE_SIZE, shift)}"
end

def decode_to_store_and_sequence(enc)
    c = enc[SHIFT_INDEX]
    shift = ALPHABET.index(c)
    store = decode(enc[0...4], shift)
    sequence = decode(enc[5..-1], shift)
    return store, sequence
end

def encode(num, pad, shift)
    base_digits = []
    constructed = []
    (0...pad).each do |power|

        digit = (num / (NUM_CHARS ** power) % NUM_CHARS).floor
        base_digits << (digit + shift + power) % NUM_CHARS
    end
    (0...base_digits.length).each do |i|
        shifted_index = (shift + i) % base_digits.length
        constructed << ALPHABET[base_digits[shifted_index]]
    end
    return constructed.reverse.join("")
end    

def decode(shifted_string, shift)
    repos = {}
    total = 0
    (0...shifted_string.length).each do |i|
        unshifted = wrap_to_positive(i - shift, shifted_string.length)
        repos[unshifted] = shifted_string[i]
    end
    (repos.length-1).downto(0) { |i|
        power = repos.length - i - 1
        some_digit = wrap_to_positive(ALPHABET.index(repos[i]) - shift - power, NUM_CHARS)
        total += some_digit * (NUM_CHARS ** power)
    }
    return total
end

def wrap_to_positive(num_to_wrap, mod_by)
    wrap = num_to_wrap
    while wrap < 0 and mod_by > 0
        wrap += mod_by
    end
    return wrap % mod_by
end

(20...25).each do |store|
    (2000...2100).each do |sequence|
        encoded = encode_store_and_sequence(store, sequence)
        dstore, dsequence = decode_to_store_and_sequence(encoded)
        puts "#{sequence} => #{encoded} => [ #{dstore} | #{dsequence} ]"
    end
end

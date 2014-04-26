#!/usr/bin/env ruby

"""
Reversible Codes

Ported from Nik's http://jsfiddle.net/nikb747/muS2P/
"""

ALPHABET = 'BCDEFGHJKMNPRSTVWXY23456789'

NUM_CHARS = ALPHABET.length
STORE_SIZE = 3
SHIFT_INDEX = 3
SEQUENCE_SIZE = 8
MOD_BY = 23 # should be less than NUM_CHARS

@verbose = false

def encode_store_and_sequence(store, sequence)
    shift = sequence % MOD_BY + 1
    enc = "#{encode(store, STORE_SIZE, shift)}#{ALPHABET[shift]}#{encode(sequence, SEQUENCE_SIZE, shift)}"
    puts "#{enc} for store=#{store} seq=#{sequence}" if @verbose
    return enc
end

def decode_to_store_and_sequence(enc)
    c = enc[SHIFT_INDEX]
    shift = ALPHABET.index(c)
    store = decode(enc[0...STORE_SIZE], shift)
    sequence = decode(enc[STORE_SIZE+1..-1], shift)
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

store_start = ARGV[0].to_i
store_end = ARGV[1].to_i
seq_start = ARGV[2].to_i
seq_end = ARGV[3].to_i

count = 0
(store_start...store_end).each do |store|
    (seq_start...seq_end).each do |sequence|
        encoded = encode_store_and_sequence(store, sequence)
        dstore, dsequence = decode_to_store_and_sequence(encoded)
        status = (store == dstore and sequence == dsequence) ? "OK" : "ERROR"
        if status == "ERROR"
          msg = "hmm #{store},#{sequence} <> #{dstore},#{dsequence}"
          $stderr.puts msg
          puts msg
        end
        count += 1
        if count % 100000 == 0
          puts "#{sequence} => #{encoded} => [ #{dstore} | #{dsequence} ] [#{status}]"
          $stderr.puts "#{count} #{store} #{sequence} #{encoded}"
        end
    end
end

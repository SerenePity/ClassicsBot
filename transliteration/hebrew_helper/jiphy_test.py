import functools

import jiphy
import re

javascript_code = """

changeElementSplit: (input, split, join) => input.split(split).join(join)

"""

s = jiphy.to.python(javascript_code)
print(s)

def comp(a, b):
    consonants = re.compile("[\u05D0-\u05F2, \uFB20-\uFB4F]")
    ligature = re.compile("[\u05C1-\u05C2]")
    dagesh = re.compile("[\u05BC, \u05BF]")  # includes rafe
    vowels = re.compile("[\u05B0-\u05BB, \u05C7]")
    accents = re.compile("[\u0590-\u05AF, \u05BD-\u05BE, \u05C0, \u05C3]")
    # since the str is split at consonants, the first a is always const, thus never flip
    if consonants.match(a):
        return 0
    # if a is anything except a consonant and b is a ligature, then flip
    if not consonants.match(a) and ligature.match(b):
        return 1
    if vowels.match(a) and dagesh.match(b):
        return 1
    if accents.match(a) and dagesh.match(b):
        return 1

def seq_helper(e):
    return ''.join(sorted(functools.cmp_to_key(comp), e.split()))

def sequence(text):
    splits = re.compile("(?=[\u05D0-\u05F2, \uFB20-\uFB4F])")
    consonants = re.compile("[\u05D0-\u05F2, \uFB20-\uFB4F]")
    ligature = re.compile("[\u05C1-\u05C2]")
    dagesh = re.compile("[\u05BC, \u05BF]")  # includes rafe
    vowels = re.compile("[\u05B0-\u05BB, \u05C7]")
    accents = re.compile("[\u0590-\u05AF, \u05BD-\u05BE, \u05C0, \u05C3]")
    return ''.join(map(seq_helper, re.split(splits, text)))


from transliteration.hebrew_helper.char_objs import hebCharsRC
from transliteration.hebrew_helper.char_objs import hebCharsRV
from transliteration.hebrew_helper.char_objs import hebCharsTrans
import re
import functools

def changeElementSplit(input, split_pattern, to_join):
    #print(input)
    #print(split_pattern)
    #print(to_join)
    # re.split(split_pattern, input)
    return re.sub(split_pattern, to_join, input)


def changeElementSubstr(input, index, join):
    return input[0, index] + join + input[index+1]

# const hebCharsRC = require('./char_objs/hebCharsRC')
# const hebCharsRV = require('./char_objs/hebCharsRV')

"""
/***
 * @param {string} text
 * @param {Object} [options]
 * @param {boolean} [options.removeVowels=false] - removes vowels in addition to cantillation marks
 * @returns {string}
 */
"""
"""
def remove(text, removeVowels=False):
    if not removeVowels:
        return text.replace(r"[\u0591-\u05F4\uFB1D-\uFB4F]", hebCharsRC.mapping[i])
    else:
        return text.replace(r"[\u0591-\u05F4\uFB1D-\uFB4F]", hebCharsRV.mapping[i])
"""


def comp(a, b):
    if a == None:
        a = 0
    if b == None:
        b = 0
    consonants = re.compile("[\u05D0-\u05F2\uFB20-\uFB4F]")
    ligature = re.compile("[\u05C1-\u05C2]")
    dagesh = re.compile("[\u05BC\u05BF]")  # includes rafe
    vowels = re.compile("[\u05B0-\u05BB, \u05C7]")
    accents = re.compile("[\u0590-\u05AF\u05BD-\u05BE\u05C0, \u05C3]")
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
    else:
        return 0

def split_helper(splits, text):
    return re.sub(splits, 'xyz', text).split('xyz')

def seq_helper(e):
    return ''.join(sorted(e.split(), key=functools.cmp_to_key(comp)))

def sequence(text):
    print("Regex: " + "(?=[\u05D0-\u05F2\uFB20-\uFB4F])")
    splits = re.compile("(?=[\u05D0-\u05F2\uFB20-\uFB4F])")
    return ''.join(map(seq_helper, split_helper(splits, text)))

def get_index(xs, target):
    indices = [i for i, x in enumerate(xs) if x == target]
    # print("indices: " + str(indices))
    if len(indices) > 0:
        return indices[0]
    else:
        return -1

def test_each(array):
    for index, element in enumerate(array):
        print("element before: " + element)
        # Tests for shin non-ligatures
        if '8' in element:
            # 8 is the shin-dot = \u05C1
            # element = changeElementSplit(element, '8', '')
            element = element.replace('8', '')

        # Tests for shin non-ligatures
        if '8' in element:
            # 8 is the shin-dot = \u05C1
            element = changeElementSplit(element, '8', '')

        # Tests for sin non-ligatures
        if '7' in element:
            # 7 is the sin-dot = \u05C2
            element = changeElementSplit(element, 'š7', 'ś')

        element = changeElementSplit(element, r"iy(?!ǝ|ĕ|ă|ŏ|i|ē|e|a|ā|ō|u|9)", 'î')

        element = changeElementSplit(element, r"ēy(?!ǝ|ĕ|ă|ŏ|i|ē|e|a|ā|ō|u|9)", 'ê')

        element = changeElementSplit(element, r"ey(?!ǝ|ĕ|ă|ŏ|i|ē|e|a|ā|ō|u|9)", 'ê')

        element = changeElementSplit(element, r"wō(?!ǝ|ĕ|ă|ŏ|i|ē|e|a|ā|u|9)", 'ô')

        element = changeElementSplit(element, r"ōw(?!ǝ|ĕ|ă|ŏ|i|ē|e|a|ā|u|9)", 'ô')

        element = changeElementSplit(element, r"w9(?!ǝ|ĕ|ă|ŏ|i|ē|e|a|ā|â|o|ô|u|û)", 'û')

        # Tests for He as a final mater or with mappiq or tests for furtive patach
        if re.compile("āh$").match(element):
            element = changeElementSplit(element, re.compile("āh$"), 'â')
        elif re.compile("ēh$").match(element):
            element = changeElementSplit(element, re.compile("ēh$"), 'ê')
        elif re.compile("eh$").match(element):
            element = changeElementSplit(element, re.compile("eh$"), 'ê')
        elif re.compile("h9$").match(element):
            element = changeElementSplit(element, re.compile("h9$"), 'h')
        elif re.compile("h9a$").match(element):
            element = changeElementSplit(element, re.compile("h9a$"), 'ah')
        elif re.compile("ḥa$").match(element):
            element = changeElementSplit(element, re.compile("ḥa$"), 'aḥ')
        elif re.compile("ʿa$").match(element):
            element = changeElementSplit(element, re.compile("ʿa$"), 'aʿ')

        if "9" in element:
            elArray = element.split()
            for i, e in enumerate(elArray):
               if e == '9' and re.compile("(a|ā|e|ē|i|î|u|û|o|ō|ô)").match(elArray[i-2]) and elArray[i-2]:
                   elArray[i] = elArray[i-1]

            element = "".join(elArray)

        # removes any remaining digits
        element = re.sub(r"[0-9]+", "", element)
        print("element after: " + element)
        array[index] = element

    return array

def tit_for_tat(text):
    ret_text = ""
    for i in text:
        if i in hebCharsTrans.mapping:
            ret_text += hebCharsTrans.mapping[i]
        if i == ' ':
            ret_text += ' '
    return ret_text

def transliterate(text):
    print(text)
    tit_tat = tit_for_tat(text)
    print(tit_tat)
    array = tit_tat.split()
    print(array)
    modArray = test_each(array)
    print(modArray)
    transliteration = ' '.join(modArray)
    return transliteration




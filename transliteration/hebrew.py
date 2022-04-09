import re

mapping = {
    # preserves white space
    ' ':      ' ',
    # # consonants
    # ## BMP
    'א':      'ʾ',
    'ב':      'b',
    'ג':      'g',
    'ד':      'd',
    'ה':      'h',
    'ו':      'w',
    'ז':      'z',
    'ח':      'ḥ',
    'ט':      'ṭ',
    'י':      'y',
    'כ':      'k',
    'ך':      'k',
    'ל':      'l',
    'מ':      'm',
    'ם':      'm',
    'נ':      'n',
    'ן':      'n',
    'ס':      's',
    'ע':      'ʿ',
    'פ':      'p',
    'ף':      'p',
    'צ':      'ṣ',
    'ץ':      'ṣ',
    'ק':      'q',
    'ר':      'r',
    'ש':      'š',
    'ת':      't',
    # ## Alphabetic Presentation Block
    '\uFB2E': 'ʾa',
    '\uFB2F': 'ʾā',
    '\uFB30': 'ʾ9',
    '\uFB31': 'b9',
    '\uFB4C': 'b',
    '\uFB32': 'g9',
    '\uFB33': 'd9',
    '\uFB34': 'h9',
    '\uFB35': 'w9',
    '\uFB4B': 'ô',
    '\uFB36': 'z9',
    '\uFB38': 'ṭ9',
    '\uFB39': 'y9',
    '\uFB3B': 'k9',
    '\uFB4D': 'k',
    '\uFB3A': 'k9',
    '\uFB3C': 'l9',
    '\uFB3E': 'm9',
    '\uFB40': 'n9',
    '\uFB41': 's9',
    '\uFB44': 'p9',
    '\uFB4E': 'p',
    '\uFB43': 'p9',
    '\uFB46': 'ṣ9',
    '\uFB47': 'q9',
    '\uFB48': 'r9',
    '\u05C1': '8',
    '\u05C2': '7',
    '\uFB2A': 'š',  # ligature for שׁ
    '\uFB2C': 'š9',
    '\uFB2B': 'ś',  # ligature for שׂ
    '\uFB2D': 'š9',
    '\uFB4A': 't9',
    # # vowels
    '\u05B0': 'ǝ',  # shewa
    '\u05B1': 'ĕ',  # hataf segol
    '\u05B2': 'ă',  # hataf patach
    '\u05B3': 'ŏ',  # hataf qamats
    '\u05B4': 'i',  # hiriq
    '\u05B5': 'ē',  # tsere
    '\u05B6': 'e',  # segol
    '\u05B7': 'a',  # patach
    '\u05B8': 'ā',  # qamats
    '\u05B9': 'ō',  # holam
    '\u05BA': 'ō',  # this is the codepoint for a holam on a const waw, but it is rarely used
    '\u05BB': 'u',  # qibbuts
    '\u05BC': '9',  # dagesh
    '\u05BD': '',  # metheg
    '\u05BE': '-',  # maqqef
    '\u05BF': '',  # rafe
    '\u05C7': 'o',  # qamets hatuf/qatan. Not used often, most use a qamats instead
    # # extra marks and cantillations
    '\u0591': '',  # athna
    '\u0592': '',
    '\u0593': '',
    '\u0594': '',
    '\u0595': '',
    '\u0596': '',
    '\u0597': '',
    '\u0598': '',
    '\u0599': '',
    '\u059A': '',
    '\u059B': '',
    '\u059C': '',
    '\u059D': '',
    '\u059E': '',
    '\u059F': '',
    '\u05A0': '',
    '\u05A1': '',
    '\u05A2': '',
    '\u05A3': '',
    '\u05A4': '',
    '\u05A5': '',
    '\u05A6': '',
    '\u05A7': '',
    '\u05A8': '',
    '\u05A9': '',
    '\u05AA': '',
    '\u05AB': '',
    '\u05AC': '',
    '\u05AD': '',
    '\u05AE': '',
    '\u05AF': '',
    '\u05C3': '',
    }


def change_element_split(input, split_pattern, to_join):
    return re.sub(split_pattern, to_join, input)


def change_element_substr(input, index, join):
    return input[0, index] + join + input[index + 1]


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


def get_index(xs, target):
    indices = [i for i, x in enumerate(xs) if x == target]
    if len(indices) > 0:
        return indices[0]
    else:
        return -1


def test_each(array):
    for index, element in enumerate(array):
        # Tests for shin non-ligatures
        if '8' in element:
            # 8 is the shin-dot = \u05C1
            # element = changeElementSplit(element, '8', '')
            element = element.replace('8', '')

        # Tests for shin non-ligatures
        if '8' in element:
            # 8 is the shin-dot = \u05C1
            element = change_element_split(element, '8', '')

        # Tests for sin non-ligatures
        if '7' in element:
            # 7 is the sin-dot = \u05C2
            element = change_element_split(element, 'š7', 'ś')

        element = change_element_split(element, r"iy(?!ǝ|ĕ|ă|ŏ|i|ē|e|a|ā|ō|u|9)", 'î')
        element = change_element_split(element, r"ēy(?!ǝ|ĕ|ă|ŏ|i|ē|e|a|ā|ō|u|9)", 'ê')
        element = change_element_split(element, r"ey(?!ǝ|ĕ|ă|ŏ|i|ē|e|a|ā|ō|u|9)", 'ê')
        element = change_element_split(element, r"wō(?!ǝ|ĕ|ă|ŏ|i|ē|e|a|ā|u|9)", 'ô')
        element = change_element_split(element, r"ōw(?!ǝ|ĕ|ă|ŏ|i|ē|e|a|ā|u|9)", 'ô')
        element = change_element_split(element, r"w9(?!ǝ|ĕ|ă|ŏ|i|ē|e|a|ā|â|o|ô|u|û)", 'û')

        # Tests for He as a final mater or with mappiq or tests for furtive patach
        if re.compile("āh$").match(element):
            element = change_element_split(element, re.compile("āh$"), 'â')
        elif re.compile("ēh$").match(element):
            element = change_element_split(element, re.compile("ēh$"), 'ê')
        elif re.compile("eh$").match(element):
            element = change_element_split(element, re.compile("eh$"), 'ê')
        elif re.compile("h9$").match(element):
            element = change_element_split(element, re.compile("h9$"), 'h')
        elif re.compile("h9a$").match(element):
            element = change_element_split(element, re.compile("h9a$"), 'ah')
        elif re.compile("ḥa$").match(element):
            element = change_element_split(element, re.compile("ḥa$"), 'aḥ')
        elif re.compile("ʿa$").match(element):
            element = change_element_split(element, re.compile("ʿa$"), 'aʿ')

        if "9" in element:
            elArray = element.split()
            for i, e in enumerate(elArray):
                if e == '9' and re.compile("(a|ā|e|ē|i|î|u|û|o|ō|ô)").match(elArray[i - 2]) and elArray[i - 2]:
                    elArray[i] = elArray[i - 1]

            element = "".join(elArray)

        # removes any remaining digits
        element = re.sub(r"[0-9]+", "", element)
        array[index] = element
    return array


def tit_for_tat(text):
    ret_text = ""
    for i in text:
        if i in mapping:
            ret_text += mapping[i]
        else:
            ret_text += i
    return ret_text


def transliterate(text):
    verses = []
    for verse in text.split("\n"):
        tit_tat = tit_for_tat(verse)
        array = tit_tat.split()
        mod_array = ' '.join(test_each(array))
        verses.append(mod_array)
    return "\n".join(verses)

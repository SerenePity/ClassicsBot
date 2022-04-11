import pykakasi

ROMANIZATION_SCHEME = 'hepburn'
ITERATION_MARKS = ['々', 'ゝ', 'ヽ ']
ABBREVIATIONS_DICT = {'ゟ': 'より', '𪜈': 'とも', 'ヿ': 'こと', '𬼀': 'シテ', '〼': 'ます', 'ヶ': '個'}


def remove_digits(s):
    return ''.join([i for i in s if not i.isdigit()])


def transliterate(text):
    text_list = []
    for i, char in enumerate(text):
        if char in ITERATION_MARKS:
            text_list.append(text_list[i - 1])
        elif char in ABBREVIATIONS_DICT:
            text_list.append(ABBREVIATIONS_DICT[char])
        else:
            text_list.append(char)
    reformatted_text = ''.join(text_list)
    kks = pykakasi.kakasi()
    result = kks.convert(reformatted_text)
    romanized = []
    for item in result:
        romanized.append(item[ROMANIZATION_SCHEME])
    return remove_digits(' '.join(romanized).replace('ou', 'о̄')).replace('  ', ' ')

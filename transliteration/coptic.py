mapping = {
        'Ⲓⲏ̅ⲥ̅':   'iēsous',
        'ⲭ̅ⲥ̅':    'christos',
        'Ⲡⲭ̅ⲥ̅':   'pachristos',
        'ⲧϩ':      't\'h', 'Ⲧϩ': 't\'h', 'ⲦϨ': 'T\'H',
        'ⲡϩ':      'p\'h', 'Ⲡϩ': 'P\'h', 'ⲠϨ': 'P\'H',
        'Ⲁ':       'A', 'ⲁ': 'a',
        'Ⲃ':       'B', 'ⲃ': 'b',
        'Ⲅ':       'G', 'ⲅ': 'g',
        'Ⲇ':       'D', 'ⲇ': 'd',
        'Ⲉ':       'E', 'ⲉ': 'e',
        'Ⲍ':       'Z', 'ⲍ': 'z',
        'Ⲏ':       'Ē', 'ⲏ': 'e',
        'Ⲑ':       'Th', 'ⲑ': 'th',
        'Ⲓ':       'I', 'ⲓ': 'i',
        'Ϊ':       'Ï', 'ϊ': 'ï',
        'Ⲕ':       'K', 'ⲕ': 'k',
        'Ⲗ':       'L', 'ⲗ': 'l',
        'Ⲙ':       'M', 'ⲙ': 'm',
        'Ⲛ':       'N', 'ⲛ': 'n',
        'Ⲝ':       'X', 'ⲝ': 'x',
        'Ⲟ':       'O', 'ⲟ': 'o',
        'Ⲡ':       'P', 'ⲡ': 'p',
        'Ⲣ':       'R', 'ⲣ': 'r',
        'Ⲥ':       'S', 'ⲥ': 's',
        'Ⲧ':       'T', 'ⲧ': 't',
        'Ⲩ':       'U', 'ⲩ': 'u',
        'Ⲫ':       'Ph', 'ⲫ': 'ph',
        'Ⲭ':       'Ch', 'ⲭ': 'ch',
        'Ⲯ':       'Ps', 'ⲯ': 'ps',
        'Ⲱ':       'Ō', 'ⲱ': 'ō',
        'Ϣ':       'Š', 'ϣ': 'š',
        'Ϥ':       'F', 'ϥ': 'f',
        'Ϩ':       'H', 'ϩ': 'h',
        'Ϫ':       'Č', 'ϫ': 'č',
        'Ϭ':       'Ky', 'ϭ': 'ky',
        'Ϯ':       'Ti', 'ϯ': 'ti',
        'Ⳉ':       'Ẍ', 'ⳉ': 'ẍ',
        'Ϧ':       'Ḥ', 'ϧ': 'ḥ',
        'Ⲳ':       'ʼ', 'ⲳ': 'ʼ',
        'Ⲹ':       'K', 'ⲹ': 'k',
        'Ⲻ':       '', 'ⲻ': '',
        '⳿':       '', '⳪': 'os',
        'Ⳃ':       'Ç', 'ⳃ': 'ç',
        'Ⳋ':       'Ç', 'ⳋ': 'ç',
        u'\u0305': ''
        }


def transliterate(text):
    for key in mapping.keys():
        text = text.replace(key, mapping[key])
    return text

from lang_trans.arabic import arabtex
import romanize3
from transliterate import translit

import transliteration.coptic
import transliteration.greek
import transliteration.hebrew
import transliteration.korean
import transliteration.mandarin
import transliteration.middle_chinese
import transliteration.old_chinese
import transliteration.japanese

COPTIC = ['bohairic', 'sahidic', 'coptic']
ARAMAIC = ['peshitta']
LATIN = ["vulgate", "newvulgates"]
HEBREW = ['aleppo', 'modernhebrew', 'bhsnovowels', 'bhs', 'wlcnovowels', 'wlc', 'codex']
ARABIC = ['arabicsv', 'nav', 'erv-ar']
GREEK = ['moderngreek', 'majoritytext', 'byzantine', 'textusreceptus', 'text', 'tischendorf', 'westcotthort',
         'westcott', 'lxxpar', 'lxx', 'lxxunaccentspar', 'lxxunaccents', 'sblgnt']
RUSSIAN = ['makarij', 'synodal', 'zhuromsky']
UKRAINIAN = ['ukr', 'ukrainian', 'ukr-uk']
BULGARIAN = ['bg1940', 'bulgarian1940', 'bulg', 'erv-bg']
SERBIAN = ['erv-sr']
GEORGIAN = ['georgian']
ARMENIAN = ['westernarmenian', 'easternarmenian']
KOREAN = ['korean', 'klb']
CHINESE = ['ccb', 'ccbt', 'erv-zh', 'cns', 'cnt', 'cus', 'cut', 'cc']
JAPANESE = ['jlb', 'meiji']


def transliterate_verse(version, text, middle_chinese=False, old_chinese=False):
    if version in COPTIC:
        text = transliteration.coptic.transliterate(text).lower()
    if version in ARAMAIC:
        r = romanize3.__dict__['syc']
        text = r.convert(text)
    if version in HEBREW:
        text = transliteration.hebrew.transliterate(text)
    if version in ARABIC:
        text = arabtex.transliterate(text)
    if version in GREEK:
        text = transliteration.greek.transliterate(text)
    if version in RUSSIAN:
        text = translit(text, 'ru', reversed=True)
    if version in BULGARIAN:
        text = translit(text, 'bg', reversed=True)
    if version in SERBIAN:
        text = translit(text, 'sr', reversed=True)
    if version in UKRAINIAN:
        text = translit(text, 'uk', reversed=True)
    if version in ARMENIAN:
        text = translit(text, 'hy', reversed=True).replace('ւ', 'v')
    if version in GEORGIAN:
        text = translit(text, 'ka', reversed=True).replace('ჲ', 'y')
    if version in KOREAN:
        text = transliteration.korean.transliterate(text)
    if version in JAPANESE:
        text = transliteration.japanese.transliterate(text)
    if version in CHINESE:
        if middle_chinese:
            text = transliteration.middle_chinese.transliterate(text)
        elif old_chinese:
            text = transliteration.old_chinese.transliterate(text)
        else:
            text = transliteration.mandarin.transliterate(text)
    return text.replace("Read full chapter", "").replace("  ", " ")

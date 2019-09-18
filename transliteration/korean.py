from hangul_romanize import Transliter
from hangul_romanize.rule import academic

def transliterate(text):
    transliter = Transliter(academic)
    return transliter.translit(text)
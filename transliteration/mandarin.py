import re

from mafan import tradify

from chinese_reconstructions import baxter_sagart
import my_wiktionary_parser


def get_pinyin_from_wiktionary(char):
    soup = my_wiktionary_parser.get_soup(char)
    if 'is  a variant' in soup.text:
        soup_bytes = str(soup).encode('utf-8')
        regular_form_pattern = re.compile(r"<i>a variant.*form of <span.*?>(.?)</span>")
        regular_form = re.search(regular_form_pattern, soup_bytes.decode('utf-8')).group(1)
        return get_pinyin_from_wiktionary(regular_form)
    pinyin = soup.find_all(attrs={'class': re.compile("form-of pinyin.*")})[0].get_text().split("(")[0].strip()
    return pinyin


def is_chinese_char(texts):
    return re.search("[\u4e00-\u9FFF]", texts)


def transliterate(text):
    ret_array = []

    for char in text:
        if not is_chinese_char(char):
            ret_array.append("‰" + char + "‰")
        else:
            char = tradify(char)
            pinyin, mc, oc_bax, gloss = baxter_sagart.get_historical_chinese(char)
            if pinyin == 'n/a':
                pinyin = get_pinyin_from_wiktionary(char).split(",")[0].strip()
            ret_array.append(pinyin)
    ret_str = " ".join(ret_array)
    for char in baxter_sagart.punctuation:
        if baxter_sagart.punctuation[char] == "«":
            ret_str = ret_str.replace(f" {char} ", f" {baxter_sagart.punctuation[char]}")
        elif baxter_sagart.punctuation[char] == "»":
            ret_str = ret_str.replace(f" {char} ", f"{baxter_sagart.punctuation[char]} ")
        else:
            ret_str = ret_str.replace(f"{char}", f"{baxter_sagart.punctuation[char]}")
            ret_str = re.sub(r"\s*([:,\.\";!?])", r"\1", ret_str)
    print(ret_str)
    return ret_str.replace("‰ ‰", "").replace(" ‰", " ").replace("‰ ", " ").replace("‰", "").replace("「", "\"").replace(
        "」", "\""
        ).replace(" \"", "\"") \
        .replace(" ,", ",").replace(" :", ": ").replace(" ?", "?").replace(" !", "!").replace(" .", ".") \
        .replace(" ;", ";") \
        .replace(": \" ", ": \"")

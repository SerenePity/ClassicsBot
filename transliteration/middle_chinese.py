from cached_antique_chinese import baxter_sagart
import re
import my_wiktionary_parser
from mafan import tradify


def get_middle_chinese_from_wiktionary(char):
    soup = my_wiktionary_parser.get_soup(char)
    try:
        middle_chinese = soup.find_all("a", attrs={"title": "w:Middle Chinese"})[0].next_sibling.next_sibling.get_text().split(",")[0].replace("/", "")
    except:
        return char
    return middle_chinese

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
            if mc == 'n/a':
                mc = get_middle_chinese_from_wiktionary(char)
            ret_array.append(mc)

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
    return ret_str.replace("‰ ‰", "").replace(" ‰", " ").replace("‰ ", " ").replace("‰", "").replace("「", "\"").replace("」", "\"").replace(" \"", "\"")\
        .replace(" ,", ",").replace(" :", ": ").replace(" ?", "?").replace(" !", "!").replace(" .", ".").replace(" ;", ";").replace(": \" ", ": \"")

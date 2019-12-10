from cached_antique_chinese import baxter_sagart
import re
import my_wiktionary_parser
from mafan import tradify
import traceback


def get_old_chinese_from_wiktionary(char):
    soup = my_wiktionary_parser.get_soup(char)
    print(soup)
    try:
        old_chinese = soup.find_all(attrs={"href": "https://en.wikipedia.org/wiki/Old_Chinese"})[0].findNextSibling("dl").get_text().replace("(Zhengzhang): ", "").replace("/", "")
    except:
        traceback.print_exc()
        return char
    return old_chinese

def is_chinese_char(texts):
    return re.search("[\u4e00-\u9FFF]", texts)

def transliterate(text):

    ret_array = []

    for char in text:
        if not is_chinese_char(char):
            ret_array.append("‰" + char + "‰")
        else:
            char = tradify(char)
            pinyin, mc, oc, gloss = baxter_sagart.get_historical_chinese(char)
            if oc == 'n/a':
                oc = get_old_chinese_from_wiktionary(char)
            ret_array.append(oc.split(",")[0].strip().replace(".", ""))

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
    ret_str = ret_str.replace("‰ ‰", "").replace(" ‰", " ").replace("‰ ", " ").replace("‰", "")\
        .replace("*", "").replace("「", "\"").replace("」", "\"").replace(" \"", "\"").replace(" ,", ",")\
        .replace(" :", ": ").replace(" ?", "?").replace(" !", "!").replace(" .", ".").replace(" ;", ";").replace(": \" ", ": \"")\
        .replace("[", "").replace("]", "").replace("-", "").replace("<", "").replace(">", "")
    ret_str = re.sub("\(.+?\)", "", ret_str)
    return ret_str

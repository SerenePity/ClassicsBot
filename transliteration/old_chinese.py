import re
import traceback

from mafan import tradify

from chinese_reconstructions import baxter_sagart
import my_wiktionary_parser


def get_old_chinese_from_wiktionary(char):
    soup = my_wiktionary_parser.get_soup(char)
    if 'is  a variant' in soup.text:
        soup_bytes = str(soup).encode('utf-8')
        regular_form_pattern = re.compile(r"<i>a variant.*form of <span.*?>(.?)</span>")
        regular_form = re.search(regular_form_pattern, soup_bytes.decode('utf-8')).group(1)
        return get_old_chinese_from_wiktionary(regular_form)
    try:
        old_chinese = soup.find_all(attrs={"href": "https://en.wikipedia.org/wiki/Old_Chinese"})[0].findNextSibling(
            "dl").get_text().replace("(Zhengzhang): ", "").replace("(Baxter–Sagart): ", "").replace("/", "") \
            .split(", ")[0].split('\n')[0]
    except:
        traceback.print_exc()
        return char
    print(f'Old Chinese for {char}: {old_chinese}')
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
            ret_array.append(oc.split(",")[0].strip())

    ret_str = " ".join(ret_array)
    for char in baxter_sagart.punctuation:
        if baxter_sagart.punctuation[char] == "«":
            ret_str = ret_str.replace(f" {char} ", f" {baxter_sagart.punctuation[char]}")
        elif baxter_sagart.punctuation[char] == "»":
            ret_str = ret_str.replace(f" {char} ", f"{baxter_sagart.punctuation[char]} ")
        else:
            ret_str = ret_str.replace(f"{char}", f"{baxter_sagart.punctuation[char]}")
            ret_str = re.sub(r"\s*([:\";!?])", r"\1", ret_str)
    ret_str = ret_str.replace("‰ ‰", "").replace(" ‰", " ").replace("‰ ", " ").replace("‰", "") \
        .replace("*", "").replace("「", "\"").replace("」", "\"").replace(" \"", "\"").replace(" ,", ",") \
        .replace(" :", ": ").replace(" ?", "?").replace(" !", "!").replace(" ;", ";").replace(": \" ", ": \"") \
        .replace("[", "").replace("]", "").replace("<", "").replace(">", "")
    return ret_str

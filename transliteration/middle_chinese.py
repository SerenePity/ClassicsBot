import re
import traceback

from mafan import tradify

from chinese_reconstructions.baxter_sagart.parser import get_reconstruction
from chinese_reconstructions.cjk_punctuations import puncutation_dict
import my_wiktionary_parser


def get_middle_chinese_from_wiktionary(char):
    soup = my_wiktionary_parser.get_soup(char)
    if 'is  a variant' in soup.text:
        soup_bytes = str(soup).encode('utf-8')
        regular_form_pattern = re.compile(r"<i>a variant.*form of <span.*?>(.?)</span>")
        regular_form = re.search(regular_form_pattern, soup_bytes.decode('utf-8')).group(1)
        return get_middle_chinese_from_wiktionary(regular_form)
    try:
        middle_chinese = soup.find_all("a", attrs={"title": "w:Middle Chinese"})[0].next_sibling.next_sibling \
            .get_text().split(",")[0].replace("/", "")
    except:
        print(f"Failed to transliterate {char}")
        traceback.print_exc()
        return char
    return middle_chinese


def is_chinese_char(texts):
    return re.search("[\u4e00-\u9FFF]", texts)


def transliterate(text):
    ret_array = []

    for char in text:
        if not is_chinese_char(char):
            if char in puncutation_dict:
                ret_array.append(puncutation_dict[char])
            else:
                ret_array.append("‰" + char + "‰")
        elif char in puncutation_dict:
            ret_array.append(puncutation_dict[char])
            print(f"Appended {puncutation_dict[char]} instead of {char}")
        else:
            char = tradify(char)
            pinyin, mc, oc, gloss = get_reconstruction(char)
            if mc == 'n/a':
                try:
                    mc = get_middle_chinese_from_wiktionary(char).split(",")[0].strip()
                except:
                    ret_array.append(char)
            ret_array.append(mc)
    ret_str = " ".join(ret_array)
    return ret_str.replace("‰ ‰", "").replace(" ‰", " ").replace("‰ ", " ").replace("‰", "").replace("「", "\"") \
        .replace("」", "\"").replace(" \"", "\"").replace(" ,", ",").replace(" :", ": ").replace(" ?", "?") \
        .replace(" !", "!").replace(" .", ".").replace(" ;", ";").replace(": \" ", ": \"").replace(', ○', '.')

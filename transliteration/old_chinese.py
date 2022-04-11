import re
import traceback

from mafan import tradify

from chinese_reconstructions.baxter_sagart.parser import get_reconstruction
from chinese_reconstructions.cjk_punctuations import puncutation_dict
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
        print(f"Failed to transliterate {char}")
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
            if char in puncutation_dict:
                ret_array.append(puncutation_dict[char])
                print(f"Appended {puncutation_dict[char]} instead of {char} because {char} is not a Chinese character")
            else:
                ret_array.append("‰" + char + "‰")
        elif char in puncutation_dict:
            ret_array.append(puncutation_dict[char])
            print(f"Appended {puncutation_dict[char]} instead of {char}")
        else:
            char = tradify(char)
            pinyin, mc, oc, gloss = get_reconstruction(char)
            if oc == 'n/a':
                try:
                    oc = get_old_chinese_from_wiktionary(char).split(",")[0].strip()
                except:
                    ret_array.append(char)
            ret_array.append(oc.replace("*", ""))
    ret_str = " ".join(ret_array)
    return ret_str.replace("‰ ‰", "").replace(" ‰", " ").replace("‰ ", " ").replace("‰", "").replace("「", "\"") \
        .replace("」", "\"").replace(" \"", "\"").replace(" ,", ",").replace(" :", ": ").replace(" ?", "?") \
        .replace(" !", "!").replace(" .", ".").replace(" ;", ";").replace(": \" ", ": \"").replace(', ○', '.')

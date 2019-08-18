from cached_antique_chinese import baxter_sagart
import re
import my_wiktionary_parser


def get_pinyin_from_wiktionary(char):
    soup = my_wiktionary_parser.get_soup(char)
    pinyin = soup.find_all(attrs={'class': re.compile("form-of pinyin.*")})[0].get_text().split("(")[0].strip()
    print(f"PINYIN: {pinyin}")
    return pinyin


def transliterate(text):

    ret_array = []

    for char in text:
        if re.match(r"([0-9A-Za-z\s\.\,\!\"\';\)\(]+)", char):
            ret_array.append("‰" + char + "‰")
        else:
            pinyin, mc, oc_bax, gloss = baxter_sagart.get_historical_chinese(char)
            if pinyin == 'n/a':
                pinyin = get_pinyin_from_wiktionary(char)
            ret_array.append(pinyin)
    ret_str = " ".join(ret_array)
    for char in baxter_sagart.punctuation:
        if baxter_sagart.punctuation[char] == "«":
            ret_str = ret_str.replace(f" {char} ", f" {baxter_sagart.punctuation[char]}")
        elif baxter_sagart.punctuation[char] == "»":
            ret_str = ret_str.replace(f" {char} ", f"{baxter_sagart.punctuation[char]} ")
        else:
            ret_str = re.sub(r"\s*([:,\.\";!?])", r"\1", ret_str)
    print(ret_str)
    return ret_str.replace("‰ ‰", "").replace(" ‰", " ").replace("‰ ", " ")
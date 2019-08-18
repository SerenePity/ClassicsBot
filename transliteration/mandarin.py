from cached_antique_chinese import baxter_sagart
import re

def transliterate(text):

    ret_array = []

    for char in list(text):
        pinyin, mc, oc_bax, gloss = baxter_sagart.get_historical_chinese(char)
        ret_array.append(pinyin)
    ret_str = " ".join(ret_array)
    for char in baxter_sagart.punctuation:
        if baxter_sagart.punctuation[char] == "«":
            ret_str = ret_str.replace(f" {char} ", f" {baxter_sagart.punctuation[char]}")
        elif baxter_sagart.punctuation[char] == "»":
            ret_str = ret_str.replace(f" {char} ", f"{baxter_sagart.punctuation[char]} ")
        else:
            ret_str = re.sub(r"\s*([:,\.\";!?])", r"\1", ret_str)
    return ret_str
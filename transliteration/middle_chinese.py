from cached_antique_chinese import baxter_sagart
import re

def transliterate(text):

    ret_array = []

    for char in text:
        if re.match(r"([0-9A-Za-z\s\.\,\!\"\';\)\(]+)", char):
            ret_array.append("‰" + char + "‰")
        else:
            pinyin, mc, oc_bax, gloss = baxter_sagart.get_historical_chinese(char)
            ret_array.append(mc)

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

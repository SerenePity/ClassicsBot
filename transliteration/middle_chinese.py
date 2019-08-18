from cached_antique_chinese import baxter_sagart

def transliterate(text):

    ret_array = []

    for char in list(text):
        pinyin, mc, oc_bax, gloss = baxter_sagart.get_historical_chinese(char)
        ret_array.append(mc)

    return " ".join(ret_array)

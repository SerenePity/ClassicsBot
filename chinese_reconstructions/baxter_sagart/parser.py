from chinese_reconstructions.baxter_sagart.reconstructions import reconstructions
from chinese_reconstructions.cjk_punctuations import puncutation_dict


def get_reconstruction(char):
    if char in puncutation_dict:
        converted = puncutation_dict[char]
        return converted, converted, converted, converted
    elif char in reconstructions:
        tuple_list = reconstructions[char]
        first_entry = tuple_list[-1]
        pinyin, mc, oc_bax, gloss = first_entry
        oc_bax = oc_bax.split(" (")[0].strip()
        return pinyin, mc, oc_bax, gloss
    else:
        return "n/a", "n/a", "n/a", "n/a"

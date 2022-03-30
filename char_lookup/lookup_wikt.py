import re
import traceback

from mafan import tradify

from chinese_reconstructions import baxter_sagart
from my_wiktionary_parser import get_soup


def lookup_baxter_sagart(char):
    if char in baxter_sagart.reconstructions:
        return [r for r in baxter_sagart.reconstructions[char]]
    elif (tradify(char)) in baxter_sagart.reconstructions:
        char = tradify(char)
        return [r for r in baxter_sagart.reconstructions[char]]
    else:
        return ["n/a", "n/a", "n/a", "n/a"]


def lookup_zhengchang(char):
    soup = get_soup(char)
    try:
        pronunciations = re.findall(r"Shangfang\".*\"IPAchar\">(.*?)<", str(soup))[0]
    except:
        try:
            char = tradify(char)
            soup = get_soup(char)
            pronunciations = re.findall(r"Shangfang\".*\"IPAchar\">(.*?)<", str(soup))[0]
        except:
            traceback.print_exc()
            return ["n/a"]
    return pronunciations.replace("/", "").split(", ")


def output_baxter_sagart(char):
    r = lookup_baxter_sagart(char)
    defs = []
    try:
        for mand, mc, oc, gloss in r:
            defs.append(f'{oc} > {mc} > {mand}: {gloss}')
        output = "\n".join(defs)
    except:
        output = 'n/a'
    return (
        f'{char}\n'
        f'Baxter-Sagart:\n'
        f'{output}'
    )


def output_zhengchang(char):
    results = "\n".join(lookup_zhengchang(char))
    return (f'Zhengzhang:\n'
            f'{results}')


def combine_outputs(char):
    return "\n\n".join([output_baxter_sagart(char), output_zhengchang(char)])

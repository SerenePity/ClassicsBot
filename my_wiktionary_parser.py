from collections import OrderedDict

import requests
import re
from bs4 import BeautifulSoup, NavigableString, Tag
import pprint
import yaml
import json

PARTS_OF_SPEECH = [
    "Noun", "Verb", "Adjective", "Adverb", "Determiner",
    "Article", "Preposition", "Conjunction", "Proper noun",
    "Letter", "Character", "Phrase", "Proverb", "Idiom",
    "Symbol", "Syllable", "Numeral", "Initialism", "Interjection",
    "Definitions", "Pronoun", "Prefix", "Suffix", "Infix", "Root"
]

def format(ul):
    ret = ""
    for li in ul.find_all("li", recursive=False):
        ul2 = li.ul.extract() if li.ul and not isinstance(li, NavigableString) else None
        ret += li.get_text()
        if ul2:
            for li in ul2:
                ret += '\n' + (li.get_text() if li and isinstance(li, NavigableString) else "") + '\n'
    return ret

def get_etymology(soup, language):
    language_header = None
    etymology = "Not found."
    for h2 in soup.find_all('h2'):
        #print(h2)
        if h2.span and h2.span.get_text() == language.title():
            language_header = h2
            break

    for sibling in language_header.next_siblings:
        if isinstance(sibling, NavigableString):
            continue
        if sibling.name == 'h2':
            break
        if 'Etymology' in sibling.get_text():
            if 'This entry lacks etymological information.' in sibling.findNextSibling('div').get_text():
                return "Not found."
            #print(sibling)
            #print(sibling.next_siblings)
            etymology = sibling.findNextSibling('p').get_text()

    return etymology

def get_definition(soup, language, include_examples=True):
    #print("Part of speech: " + part_of_speech.title())
    language_header = None
    definition = "Not found."
    for h2 in soup.find_all('h2'):
        #print(h2)
        if h2.span and h2.span.get_text() == language.title():
            language_header = h2
            break
    if not language_header:
        return "Could not find definition."
    #print(language_header)
    definition = language_header.findNextSibling('ol')
    #print(definition)
    if not include_examples:
        print("Removing examples")
        for ul in definition(["ul"]):
            ul.extract()
    else:
        for ul in definition(["ul", "dl"]):
            for li in ul(['li', 'dl']):
                if li.dl:
                    li.dl.string = '\n'.join(["\t" + s for s in li.dl.get_text().split('\n')])
                elif li.ul:
                    li.ul.string = '\n'.join(["\t" + s for s in li.ul.get_text().split('\n')])
                li.string = '\n'.join(['\t' + t for t in li.get_text().split('\n')])
    return definition

def remove_example(li):
    li.ul.extract() if li.ul else li

"""
def get_definition(soup, part_of_speech):
    h3s = soup.find_all('h3')
    defs = []
    for h3 in h3s:
        if h3.span and h3.span.has_attr('id') and h3.span['id'] == part_of_speech:
            ol = h3.next_sibling.next_sibling.next_sibling.next_sibling
            for li in ol:
                definition = ""
                try:
                    definition = li.get_text()
                except:
                    continue
                defs.append(definition.replace("\"", "").replace("'",""))
    return defs
"""

def get_word(soup, language, word):
    language_header = None
    found_word = ""
    for h2 in soup.find_all('h2'):
        # print(h2)
        if h2.span and h2.span.get_text() == language.title():
            language_header = h2
            break

    for sibling in language_header.next_siblings:
        if isinstance(sibling, NavigableString):
            continue
        if sibling.name == 'h2':
            break
        if sibling.name == 'h3' and sibling.span and sibling.span.get_text() in PARTS_OF_SPEECH:
            word = sibling.findNextSibling('p').get_text()

    return word

def get_definitions(soup, language, include_examples=True):
    definitions = get_definition(soup, language, include_examples)
    definitions = [li.get_text() for li in definitions if not isinstance(li, NavigableString)]

    print("Definitions " + str(definitions))
    return [d for d in definitions if d != None and d.strip() != ""]

def get_soup(word):
    print(f"https://en.wiktionary.org/wiki/{word}")
    return BeautifulSoup(requests.get(f"https://en.wiktionary.org/wiki/{word}").text)

def parse_table(ul):
    descendants = []
    for ul in ul:
        if not isinstance(ul, NavigableString):
            descendants.append(ul.li)
    return descendants


def dictify(ul, level=0):
    return_str = ""
    for li in ul.find_all("li", recursive=False):
        key = next(li.stripped_strings)
        print("Key: " + key)
        nukes = ' '.join([s.text if isinstance(s, Tag) else s for s in li.find_all('span', recursive=False)])
        return_str +=  level*'\t\t' + key + " " + nukes + '\n'

        #print("Spans: " + str([s.text for s in li.find_all('span')]))
        ul2 = li.find("ul")
        if ul2:
            return_str += '\t\t'*(level + 1) + dictify(ul2, level +  1).strip() + '\n'
    print(return_str)
    return return_str.strip()

def get_derivations(soup, language):
    language_header = None
    for h2 in soup.find_all('h2'):
        # print(h2)
        if h2.span and h2.span.get_text() == language.title():
            language_header = h2
            break
    for sibling in language_header.next_siblings:
        if isinstance(sibling, NavigableString):
            continue
        if sibling.name == 'h2':
            break
        if sibling.name == 'h4' and sibling.span and not isinstance(sibling.span, NavigableString) and sibling.span.get_text() in ['Derived terms', 'Descendants']:
            ul = None
            for h4 in soup.find_all('h4'):
                if h4.span and not isinstance(h4.span, NavigableString) and h4.span.get_text() in ['Descendants', 'Derived terms']:
                    uls = h4.find_next_siblings('ul')
                    break
            if not uls:
                return "Not found."
            else:
                return '\n\n'.join(["**" + re.sub(r"\[(.*?)\]", "", ul.find_previous_siblings(['h4', 'h3'])[0].text).strip() + "**" + '\n' + dictify(ul, 0) for ul in uls if 'References' not in ul.get_text() and 'See also' not in ul.get_text()])
    return "Not found."


def pretty(d, indent=0):
   ret = ""
   for key, value in d.items():
      ret += ('\t' * indent + str(key))
      if isinstance(value, dict):
            n = pretty(value, indent+1)
            if n:
                ret += n

      else:
          ret += '\t' * (indent+1) + str(value)

soup = get_soup("Reconstruction:Proto-Indo-European/lewk-")
deriv_dict = get_derivations(soup, "Proto-Indo-European")
print('============================')
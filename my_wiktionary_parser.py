import requests
import re
from bs4 import BeautifulSoup, NavigableString

PARTS_OF_SPEECH = [
    "Noun", "Verb", "Adjective", "Adverb", "Determiner",
    "Article", "Preposition", "Conjunction", "Proper noun",
    "Letter", "Character", "Phrase", "Proverb", "Idiom",
    "Symbol", "Syllable", "Numeral", "Initialism", "Interjection",
    "Definitions", "Pronoun", "Prefix", "Suffix", "Infix", "Root"
]


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

def get_definition(soup, language):
    #print("Part of speech: " + part_of_speech.title())
    language_header = None
    definition = "Not found."
    for h2 in soup.find_all('h2'):
        #print(h2)
        if h2.span and h2.span.get_text() == language.title():
            language_header = h2
            break

    #print(language_header)
    definition = language_header.findNextSibling('ol')
    #definition = [s for s in language_header.next_siblings if s.name == 'p' ]
    #print(
    #'=======================\n'.join(
    #    [str(i) for i in list(language_header.next_siblings)])
    #)
    return definition

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

def get_definitions(soup, language):
    definitions = get_definition(soup, language)

    definitions = [li.get_text() for li in definitions if not isinstance(li, NavigableString)]
    print("Definitions " + str(definitions))
    return [d for d in definitions if d != None and d.strip() != ""]

def get_soup(word):
    return BeautifulSoup(requests.get(f"https://en.wiktionary.org/wiki/{word}").text)

"""
soup = get_soup("sanna")
print(get_etymology(soup, "Icelandic"))
print(get_definitions(soup, "Icelandic"))

soup = get_soup("vir")
print(get_etymology(soup, "Latin"))
print(get_definitions(soup, "Latin"))


soup = get_soup("man")
print(get_etymology(soup, "English"))
print(get_definitions(soup, "English"))

soup = get_soup("sanna")
print(get_etymology(soup, ""))
print(get_definitions(soup, "Icelandic"))

soup = get_soup("sanna")
print(get_etymology(soup, "Latin"))
print(get_definitions(soup, "Icelandic"))
"""
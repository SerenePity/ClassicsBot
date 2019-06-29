import requests
import re
from bs4 import BeautifulSoup

PARTS_OF_SPEECH = [
    "noun", "verb", "adjective", "adverb", "determiner",
    "article", "preposition", "conjunction", "proper noun",
    "letter", "character", "phrase", "proverb", "idiom",
    "symbol", "syllable", "numeral", "initialism", "interjection",
    "definitions", "pronoun", "prefix", "suffix", "infix", "root"
]


def get_language_entry(url, language):
    response_text = requests.get(url).text
    soup = BeautifulSoup(response_text)
    content_list = soup.find_all('div', {"id": "mw-content-text"})
    for content in content_list:
        children = content.descendants
        for child in children:
            # print(child)
            if child and language in child:
                #print("Found")
                #print(content)
                return content
    return None

def get_trait(soup, trait):

    h3s = soup.find_all('h3')
    for h3 in h3s:
        if h3.span and h3.span['id'] == trait:
            return h3.next_sibling.next_sibling.get_text().strip()

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

def get_etymology(soup):
    return get_trait(soup, "Etymology")
#print(soup)

def get_definitions(soup):
    definitions = []
    for part_of_speech in PARTS_OF_SPEECH:
        definitions.append(get_definition(soup, part_of_speech.title()))
    return definitions
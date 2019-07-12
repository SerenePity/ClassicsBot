from collections import OrderedDict

import requests
import re
from mafan import simplify, tradify
from bs4 import BeautifulSoup, NavigableString, Tag
import traceback

PARTS_OF_SPEECH = [
    "Noun", "Verb", "Adjective", "Adverb", "Determiner",
    "Article", "Preposition", "Conjunction", "Proper noun",
    "Letter", "Character", "Phrase", "Proverb", "Idiom",
    "Symbol", "Syllable", "Numeral", "Initialism", "Interjection",
    "Definitions", "Pronoun", "Prefix", "Suffix", "Infix", "Root"
]

GRAMMAR_KEYWORDS = {'first-person', 'second-person', 'third-person', 'singular', 'plural', 'nominative', 'accusative', 'genitive',
     'ablative', 'dative', 'vocative', 'locative', 'instrumental', 'masculine', 'feminine', 'neuter', 'indicative', 'subjunctive', 'perfect', 'imperfect',
     'present', 'imperfect', 'aorist', 'mediopassive'}

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
        if h2.span and language.title() in [s.get_text().strip() for s in h2.find_all('span')]:
            language_header = h2
            break

    if not language_header:
        return "Not found."

    for sibling in language_header.next_siblings:
        if isinstance(sibling, NavigableString):
            continue
        if sibling.name == 'h2':
            break
        if 'Etymology' in sibling.get_text():
            if isinstance(sibling.findNextSibling('div'), Tag) and 'This entry lacks etymological information.' in sibling.findNextSibling('div').get_text():
                return "Not found."
            try:
                dls = sibling.find_next_siblings('dl')
                if not dls or len(list(dls)) == 0:
                    etymology = sibling.findNextSibling('p').get_text()
                    if etymology and etymology.strip() != "":
                        break
                else:
                    etymology = sibling.findNextSibling('p').get_text()
                    if etymology and etymology.strip() != "":
                        break
            except:
                return "Not found."
    return etymology

def get_definition(soup, language, include_examples=True):
    #print("Part of speech: " + part_of_speech.title())
    language_header = None
    definition = "Not found."
    for h2 in soup.find_all('h2'):
        #print(h2)
        if h2.span and language.title() in [s.get_text().strip() for s in h2.find_all('span')]:
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

def get_word(soup, language, word):
    language_header = None
    found_word = ""
    for h2 in soup.find_all('h2'):
        # print(h2)
        if h2.span and language.title() in [s.get_text().strip() for s in h2.find_all('span')]:
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
    definitions = [li.get_text() if not (isinstance(li, NavigableString) or isinstance(li, str)) else li for li in definitions]

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

def old_dictify(ul, level=0):
    return_str = ""
    for li in ul.find_all("li", recursive=False):
        key = next(li.stripped_strings)
        print("Key: " + key)
        nukes = ' '.join([s.text if isinstance(s, Tag) else s for s in li.find_all('span', recursive=False)]).replace(key, "")
        return_str +=  level*'\t\t' + key + " " + nukes + '\n'

        #print("Spans: " + str([s.text for s in li.find_all('span')]))
        ul2 = li.find("ul")
        if ul2:
            return_str += '\t\t'*(level + 1) + old_dictify(ul2, level +  1).strip() + '\n'
    return return_str.strip()

def dictify(ul, level=0):
    print("In Dictify")
    return_str = ""
    for li in ul.find_all("li", recursive=False):
        stripped = iter([s for s in li.stripped_strings if s not in ['⇒', '→']])
        key = next(stripped)
        nukes = ' '.join([s.text if isinstance(s, Tag) else s for s in li.find_all(name=['span', 'dl', 'cite', 'b', 'i', 'a', 'small'], recursive=False)])
        if not nukes:
            continue
        if key.strip().lower() == nukes.split()[0].lower().strip():
            key = nukes.strip()
            nukes = ""
        return_str += level*'\t\t' + key + " " + nukes + '\n'

        #print("Spans: " + str([s.text for s in li.find_all('span')]))
        ul2 = li.find("ul")
        if ul2:
            return_str += '\t\t'*(level + 1) + dictify(ul2, level +  1).strip() + '\n'
    #print(return_str)
    return return_str.strip()

def has_unwanted_headers(header):
    unwanted_list = ['References', 'See also', 'Further reading']
    for unwanted in unwanted_list:
        if unwanted in header:
            return True
    return False

def has_wanted_text(text):
    wanted_list = ['Derived terms', 'Descendants', 'Pronunciation', 'Synonyms', 'Antonyms']
    for wanted in wanted_list:
        if text.strip() in wanted:
            return True
    return False

def get_derivations(soup, language, misc=False):

    greek_tables = soup.find_all('div', {'class': 'NavFrame grc-decl grc-adecl'})
    for table in greek_tables:
        table.extract()
    latin_tables = soup.find_all('table')
    for table in latin_tables:
        table.extract()
    latin_tables = soup.find_all('table')
    for table in latin_tables:
        table.extract()
    language_header = None
    for h2 in soup.find_all('h2'):
        # print(h2)
        if h2.span and language.title() in [s.get_text().strip() for s in h2.find_all('span')]:
            language_header = h2
            break
    if not language_header:
        return '\n\n'.join(["**Derivarives**" + '\n' + "None found."])
    for sibling in language_header.next_siblings:
        if isinstance(sibling, NavigableString):
            continue
        if sibling.name == 'h2':
            break
        if sibling.name == 'h4' and sibling.span and not isinstance(sibling.span, NavigableString) and any(has_wanted_text(s) if isinstance(s, NavigableString) else has_wanted_text(s.get_text().strip()) for s in sibling.span.contents):
            ul = None
            uls = []
            for e in sibling.next_siblings:
                if e.name == 'h2':
                    break
                if e.name == 'ul':
                    uls.append(e)
                    """
                    for li in e.find_all('li'):
                        
                        for s in e.span.contents:
                            if not isinstance(e.span, NavigableString) and e.span.get_text() in ['Descendants', 'Derived terms']:
                                for ele in e.find_next_siblings():
                                    if ele.name == 'ul':
                                        uls.append(ele)"""
            if not uls:
                return "Not found."
            else:
                if misc:
                    misc = get_misc(uls)
                    return '\n\n'.join(["**" + re.sub(r"\[(.*?)\]", "", ul.find_previous_siblings(['h4', 'h3'])[0].text).strip() + "**" + '\n' + dictify(ul, 0) for ul in uls] + misc)
                else:
                    return '\n\n'.join(["**" + re.sub(r"\[(.*?)\]", "", ul.find_previous_siblings(['h4', 'h3'])[0].text).strip() + "**" + '\n' + old_dictify(ul, 0) for ul in uls if 'References' not in ul.get_text() and 'See also' not in ul.get_text()])
    return "Not found."

def get_misc(uls):
    novel_headers = ['Descendants']
    for ul in uls:
        header_dict = dict()
        misc = dictify(ul)
        header = ul.find_previous_siblings(['h4', 'h3'])[0].text.strip()
        if not has_unwanted_headers(header) and header in novel_headers:
            header_dict["**" + re.sub(r"\[(.*?)\]" + "", "", header) + "**"] += misc
    return [key.strip() + '\n' + header_dict[key].strip() for key in header_dict]

def is_grammar_def(word):
    return any(w.lower() in GRAMMAR_KEYWORDS for w in word.lower().split())

def get_latin_grammar_forms(no_macrons=False, tries=0):
    if tries > 10:
        return [None, None]
    soup = BeautifulSoup(requests.get(f"https://en.wiktionary.org/wiki/Special:RandomInCategory/Latin_non-lemma_forms").text)
    #print(soup)
    language_header = None
    headword = None
    headword_forms = []
    for h2 in soup.find_all('h2'):
        # print(h2)
        if h2.span and 'Latin' in [s.get_text().strip() for s in h2.find_all('span')]:
            language_header = h2
            break

    conjugated = None
    for sibling in language_header.next_siblings:
        if conjugated:
            break
        if isinstance(sibling, NavigableString):
            continue
        if sibling.name == 'p' and sibling.p and sibling.p.get('class') == 'Latn headword':
            conjugated = sibling.get_text()
        if sibling.name == 'ol':
            for li in sibling:
                if isinstance(li, Tag) and is_grammar_def(li.get_text()):
                    headword = li.find_parent().findPreviousSibling('p')
                    if headword.span:
                        headword.span.extract()
                    headword = headword.get_text().replace('\xa0f', '').strip()
                    headword_forms.append(li.get_text())
        if sibling.name == 'h2':
            break
    if headword_forms == []:
        headword_forms = [get_etymology(soup, 'Latin')]
    if headword == None:
        return get_latin_grammar_forms(tries + 1)
    if no_macrons:
        return [remove_macrons(headword), [remove_macrons(s) for s in headword_forms]]
    else:
        return [headword, headword_forms]

def get_greek_grammar_forms(tries=0):
    if tries > 10:
        return [None, None]
    soup = BeautifulSoup(requests.get(f"https://en.wiktionary.org/wiki/Special:RandomInCategory/Ancient_Greek_non-lemma_forms").text)
    #print(soup)
    language_header = None
    headword = None
    headword_forms = []
    for h2 in soup.find_all('h2'):
        # print(h2)
        if h2.span and 'Ancient Greek' in [s.get_text().strip() for s in h2.find_all('span')]:
            language_header = h2
            print("Language header: " + language_header.get_text())
            break

    for sibling in language_header.next_siblings:
        if isinstance(sibling, NavigableString):
            continue
        if sibling.name == 'p' and sibling.p and sibling.p.get('class') == 'Latn headword':
            conjugated = sibling.get_text()
        if sibling.name == 'ol':
            for li in sibling:
                if isinstance(li, Tag) and is_grammar_def(li.get_text()):
                    headword = li.find_parent().findPreviousSibling('p')
                    if headword.span:
                        headword.span.extract()
                    headword = headword.get_text().replace('\xa0f', '').strip()
                    headword_forms.append(li.get_text())
        if sibling.name == 'h2':
            break
    if headword_forms == []:
        headword_forms = [get_etymology(soup, 'Ancient Greek')]
    if headword == None:
        return get_greek_grammar_forms(tries + 1)
    return [headword.split('•')[0].strip(), headword_forms]

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

def get_grammar_question(language, tries=0):
    if tries > 5:
        return [None, None]
    print(language)
    soup = BeautifulSoup(requests.get(f"https://en.wiktionary.org/wiki/Special:RandomInCategory/{language.title()}_non-lemma_forms").text)
    #print(soup)
    print(f"https://en.wiktionary.org/wiki/Special:RandomInCategory/{language.title()}_non-lemma_forms")
    language_header = None
    headword = None
    headword_forms = []
    if "proto" in language.lower():
        for h1 in soup.find_all('h1'):
            if language.lower() in h1:
                language_header = h1

    for h2 in soup.find_all('h2'):
        # print(h2)
        if h2.span and language.title() in [s.get_text().strip() for s in h2.find_all('span')]:
            if not language_header:
                language_header = h2
            print("Language header: " + language_header.get_text())
            break

    for sibling in language_header.next_siblings:
        if isinstance(sibling, NavigableString):
            continue
        if sibling.name == 'p' and sibling.p and sibling.p.get('class') == 'Latn headword':
            conjugated = sibling.get_text()
        if sibling.name == 'ol':
            for li in sibling:
                if isinstance(li, Tag) and is_grammar_def(li.get_text()):
                    headword = li.find_parent().findPreviousSibling('p')
                    if headword.span:
                        headword.span.extract()
                    headword = headword.get_text().replace('\xa0f', '').strip()
                    headword_forms.append(li.get_text())
        if sibling.name == 'h2':
            break
    if headword_forms == []:
        headword_forms = [get_etymology(soup, language.title())]
    if headword == None:
        return get_grammar_question(language, tries + 1)
    return [headword.split('•')[0].strip(), headword_forms]

def get_middle_chinese_only(c):
    print("Middle Chinese only char: " + c)
    soup = get_soup(c)
    #print(soup)
    matcher = r"title=\"w:Middle Chinese\">Middle Chinese</a>: <span style=\"font-size:[0-9]+%\"><span class=\"IPA\">/(.*?)/</span>"
    try:
        pronunciation = re.findall(matcher, str(soup))[0]
    except:
        return "Not found."
    pronunciation = re.sub(r"<.*?/*>", "", pronunciation)
    return pronunciation

def get_old_chinese_only_zhengchang(c):
    print("Old Chinese only char: " + c)
    soup = get_soup(c)
    pronunciation = ""
    try:
        pronunciation = re.findall(r"Shangfang\".*\"IPAchar\">/(.*?)/", str(soup))[0]
    except:
        traceback.print_exc()
        return "Not found."
    return pronunciation

def get_old_chinese_only_sagart(c):
    print("Old Chinese only char: " + c)
    soup = get_soup(c)
    pronunciation = ""
    try:
        pronunciation = re.findall(r"Sagart\".*\"IPAchar\">/(.*?)/", str(soup))[0]
    except:
        traceback.print_exc()
        return "Not found."
    return pronunciation

def get_middle_chinese(soup, word):
    print("Chinese char: " + word)
    language_header = None
    for h2 in soup.find_all('h2'):
        # print(h2)
        if h2.span and 'Chinese' in [s.get_text().strip() for s in h2.find_all('span')]:
            language_header = h2
            break

    pronunciation = "Not found."
    for sibling in language_header.next_siblings:
        siblings = '|'.join((list([s.get_text() if (isinstance(s, Tag) and not isinstance(s, str)) else s for s in language_header.next_siblings])))
        #print(siblings)
        mc = '-'.join(' '.join([s.split('|')[0] for s in re.findall(r"Middle Chinese:\s/(.*?)", siblings)]).split()).replace('/', '')

        mc_list = []
        if not mc:
            mc_list = []
            for c in list(word):
                if c == '，':
                    mc_list.append(", ")
                else:
                    mc_list.append(get_middle_chinese_only(c).split('|')[0])
            mc = ' '.join([s.split(', ')[0] for s in mc_list]).replace('/', '')

        if not mc:
            mc_pronunciation = "Middle Chinese: Not found"
        else:
            mc_pronunciation = "Middle Chinese: " + mc
        oc_zc = []
        for c in list(word):
            if c == '，':
                oc_zc.append(", ")
            else:
                oc_zc.append(get_old_chinese_only_zhengchang(c))
        oc_sg = []
        for c in list(word):
            if c == '，':
                oc_sg.append(", ")
            else:
                oc_sg.append(get_old_chinese_only_sagart(c))
        oc_pronunciation_zc = "Old Chinese (Zhengchang): " + ' '.join(oc_zc).replace("*", "\*")
        oc_pronunciation_sg = "Old Chinese (Baxter-Sagart): " + ' '.join(oc_sg).replace("*", "\*")
        mandarin_pronunciation = "Mandarin: " + ''.join(re.findall(r"\(Pinyin\)\:\s*(.*?)\n", siblings))
        pronunciation = '\n'.join([oc_pronunciation_zc, oc_pronunciation_sg, mc_pronunciation, mandarin_pronunciation])
        return pronunciation
    return pronunciation

def get_glyph_origin_multiple(words):
    final = []
    for c in words:
        print("Charlist mem: " + c)
        soup = get_soup(c)
        final.append(f"**{c}**: {get_glyph_origin(soup)}")
    return '\n'.join(final)

def get_glyph_origin(soup):
    origin = []
    for h2 in soup.find_all('h2'):
        # print(h2)
        if h2.span and 'Chinese' in [s.get_text().strip() for s in h2.find_all('span')]:
            language_header = h2
            break

    for h3 in soup.find_all('h3'):
        #print("H3: " + str(h3))
        if h3.span and 'Glyph origin' in h3.span.get_text():
            #print("In glyph origin")
            for sibling in h3.next_siblings:
                if sibling.name == 'p':
                    origin.append(sibling.get_text())
                if sibling.name == 'h3':
                    break
    return '\n'.join(origin).strip()

mapping = {
    'Ā': 'A',
    'Ē': 'E',
    'Ī': 'I',
    'Ō': 'O',
    'Ū': 'U',
    'ā': 'a',
    'ē': 'e',
    'ī': 'i',
    'ō': 'o',
    'ū': 'u',
}

def remove_macrons(text):
    for key in mapping.keys():
        text = text.replace(key, mapping[key])
    return text

soup = get_soup('奴')
#print(soup)
print(get_glyph_origin(soup))

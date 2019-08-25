# coding=utf8
import pprint
from cached_antique_chinese import baxter_sagart

import requests
import re
from mafan import simplify, tradify
from bs4 import BeautifulSoup, NavigableString, Tag
import traceback

PARTS_OF_SPEECH = [
    "Noun", "Verb", "Adjective", "Adverb", "Determiner",
    "Article", "Preposition", "Postposition", "Conjunction", "Proper noun",
    "Letter", "Character", "Phrase", "Proverb", "Particle", "Idiom", "Participle",
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

def format_row(row, longest_len, is_line=False):
    vertical = "│"
    ret_str = vertical
    if is_line:
        return "├" + '┼'.join([(longest_len + 1) * "─" for i in range(len(row))]) + "┤"
    for i,word in enumerate(row):
        length = len(word)
        num_spaces = longest_len - length
        ret_str += " " + word + " "*num_spaces + vertical

    return ret_str

def process_entry(h):
    colspan = None
    if h.has_attr('rowspan') and not h.get_text().strip():
        return None, None
    for br in h.find_all('br'):
        br.replaceWith(", ")
    if h.has_attr('colspan'):
        colspan = int(h['colspan'])
    return (h.get_text().strip(), colspan)


def get_longest_in_col(table_array, col_num):
    max_in_col = 0
    longest_word = ""
    for row in table_array:
        word_length = len(row[col_num][0].strip())
        if word_length > max_in_col:
            max_in_col = word_length
            longest_word = row[col_num][0].strip()
    print(f"Longest word in column {col_num} is {longest_word} with length {max_in_col}")
    return max_in_col

def parse_table(table: Tag):
    table_array = []
    tbody = table.find_all('tbody')[0]
    row_soup = tbody.find_all('tr')
    max_cols = 0
    for row in row_soup:
        row_cols = [col for col in row.find_all('th') if col.get_text().strip() != ""] + [col for col in row.find_all('td') if col.get_text().strip() != ""]
        print(f"Row Cols of length {len(row_cols)}: {str(row_cols)}")
        if len(row_cols) > max_cols:
            max_cols = len(row_cols)

    print("Max cols: " + str(max_cols))
    longest_word_length = 0
    #print("row_soup: " + str(row_soup))
    #print("Length of row_soup: " + str(len(row_soup)))
    for i,row in enumerate(row_soup):
        ths = row.find_all('th')
        tds = row.find_all('td')
        row_str = list(filter(lambda x: x[0], [process_entry(h) for h in ths] + [process_entry(h) for h in tds]))
        if len(row_str) < max_cols:
            diff = (max_cols - len(row_str))
            for i in range(diff):
                row_str.append((" ", None))
        can_append = True
        for col,_ in row_str:
            if "Notes:" in col:
                can_append = False
        if can_append:
            table_array.append(row_str)
        if len(tds) == 0:
            table_array.append([("‰", None)]*max_cols)
    for row in table_array:
        for word, colspan in row:
            print("Get length of: " + word + " - " + str(len(word)))
            length = len(word)
            if length > longest_word_length:
                longest_word_length = length
    print("Longest length: " + str(longest_word_length))
    longest_word_length += 1
    pprint.pprint(table_array)
    max_word_in_col_dict = dict()
    for i,row in enumerate(table_array):
        for j in range(len(row)):
            longest_in_col = get_longest_in_col(table_array, j)
            max_word_in_col_dict[j] = longest_in_col
    top_line = "┌" + '┬'.join(["─"*(max_word_in_col_dict[i] + 1) for i in range(max_cols)]) + "┐"
    display_table = '\n'.join([format_row2(row, max_word_in_col_dict) if "‰" != row[0][0] else format_row2(row, max_word_in_col_dict, True) for i,row in enumerate(table_array)])
    bottom_line = "└" + '┴'.join(["─"*(max_word_in_col_dict[i] + 1) for i in range(max_cols)]) + "┘"

    return "```md\n" + top_line + "\n" + display_table + "\n" + bottom_line + "```"

def format_row2(row, max_word_in_col_dict, is_line = False):
    vertical = "│"
    if is_line and not any(i[1] for i in row):
        return "├" + '┼'.join(["─"*(max_word_in_col_dict[i] + 1) for i in range(len(row))]) + "┤"
    else:
        colspans = [r for r in row if r[1]]
        non_colspans = [r for r in row if not r[1]]
        print("Num of colspans: " + str(len(colspans)))
        print("Num of non-colspans: " + str(len(non_colspans)))
        ret_str = vertical
        if colspans:
            for i,r in enumerate(row):
                word = r[0]
                colspan = r[1]
                if colspan:
                    ret_str += (colspan) * (max_word_in_col_dict[i] * " ")[0:(colspan) * (max_word_in_col_dict[i] - len(word) + 1)] + " " + word
                    if i == len(row) - 1:
                        ret_str += (colspan) * (max_word_in_col_dict[i] * " ")[0:(colspan) + 1]
                else:
                    ret_str += (max_word_in_col_dict[i] - len(word) + 1)*" " + word + vertical
        else:
            ret_str = (vertical + vertical.join([(max_word_in_col_dict[i] - len(word) + 1)*" " + word for i, (word, colspan) in enumerate(row)]) + vertical)
        return ret_str
    """
    for i, (word, colspan) in enumerate(row):
        if colspan:
            ret_str += word
            print(f"Word: {word}, Colspan: {colspan}")
            for j in range(colspan - 1):
                ret_str += (max_word_in_col_dict[i + j] + 1)*" " + " "
            ret_str.replace(" ", "", len(word))
            ret_str += " " + vertical
        else:
            ret_str += word + (max_word_in_col_dict[i] - len(word) + 1)*" " + vertical
            #ret_str += vertical + vertical.join([word + (max_word_in_col_dict[i] + 1 - len(word))*" " for i, (word, colspan) in enumerate(row)]) + vertical
    return ret_str"""

def get_etymology(language_header, language, word):
    next_siblings = language_header.next_siblings
    #print(language_header)
    if "Wiktionary does not yet have an entry for " in str(next_siblings):
        return "Not found."
    etymology = "Not found."

    if not language_header:
        return "Not found."
    finished_first_ety = False
    for sibling in language_header.next_siblings:
        if isinstance(sibling, NavigableString):
            continue
        if sibling.name == 'h2':
            break
        if 'Etymology' in sibling.get_text():
            etymology = []
            if isinstance(sibling.findNextSibling('div'), Tag) and 'This entry lacks etymological information.' in sibling.findNextSibling('div').get_text():
                return "Not found."
            try:
                ety_sect = sibling.findNextSibling('p')
                etymology.append(ety_sect.get_text())
                while True:
                    ety_sect = ety_sect.findNextSibling()
                    if isinstance(ety_sect, Tag):
                        if ety_sect.name in ['h3', 'h4']:
                            finished_first_ety = True
                            break
                        etymology.append(ety_sect.get_text())
                    else:
                        etymology.append(" ")
                if finished_first_ety:
                    break
            except:
                return "Not found."
    #print(etymology)
    if etymology == "Not found.":
        return "Not found."
    return '\n'.join([p.strip() for p in etymology]).replace("[▼ expand/hide]", "\n").replace("simp.]", "simp.]\n").replace("[Pinyin]", "[Pinyin]\n")

def get_definition(soup, language, include_examples=True):
    #print("Part of speech: " + part_of_speech.title())
    if "Wiktionary does not yet have an entry for " in str(soup):
        return "Not found."
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
    #print(definition)
    return definition

def remove_example(li):
    li.ul.extract() if li.ul else li

def get_word(soup, language, word):
    if "Wiktionary does not yet have an entry for " in str(soup):
        return "Not found."
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
    if definitions == "Could not find definition.":
        return [definitions]
    definitions = [li.get_text() if not (isinstance(li, NavigableString) or isinstance(li, str)) else li for li in definitions]
    return [d for d in definitions if d != None and d.strip() != ""]

def get_soup(word):
    print(f"https://en.wiktionary.org/wiki/{word}")
    return BeautifulSoup(requests.get(f"https://en.wiktionary.org/wiki/{word}").text.replace("<!-->", ""))

def old_dictify(ul, level=0):
    return_str = ""
    for li in ul.find_all("li", recursive=False):
        key = next(li.strings)
        nukes = ' '.join([s.get_text() if isinstance(s, Tag) else s for s in li]).replace(key, "")
        #print("Key: " + key + ", Nukes: " + nukes)
        if key.strip() == 'Carl Meissner; Henry William Auden (1894)':
            nukes = nukes.split(":")[0] + ":"
        return_str +=  level*'\t\t' + key + " " + nukes + '\n'

        #print("Spans: " + str([s.text for s in li.find_all('span')]))
        ul2 = li.find("ul")
        if ul2:
            return_str += '\t\t'*(level + 1) + old_dictify(ul2, level +  1).strip() + '\n'
    return return_str.strip()

def dictify(ul, level=0):
    print("In Dictify")
    return_str = ""
    try:
        for li in ul.find_all("li", recursive=False):
            stripped = iter([s for s in li.stripped_strings if s not in ['⇒', '→']])
            try:
                key = next(stripped)
            except:
                key = ""
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
    except:
        traceback.print_exc()

    #print(return_str)
    return "Not found."

def destroy_translations(soup):
    translations = soup.find_all(text="Translations")
    print("Latin correlatives: " + str(translations))
    if translations:
        for tr in translations:
            if tr.parent.name == 'h5':
                tr.parent.decompose()
            if isinstance(tr, Tag):
                tr.decompose()
            else:
                tr.string = ""

    for t in soup.find_all('table', attrs={'class': 'translations'}):
        print("Destroying table")
        t.parent.parent.decompose()
        t.decompose()
    #print("Soup Afterwards: " + str(soup))

def destroy_latin_correlatives(soup):
    latin_correlatives_title = soup.find_all(text="Latin correlatives")
    print("Latin correlatives: " + str(latin_correlatives_title))
    if latin_correlatives_title:
        for lc in latin_correlatives_title:
            lc.decompose() if isinstance(lc, Tag) else lc.replace_with("")

    related_terms = soup.find_all('span', text="Related terms")
    for rt in related_terms:
        rt.parent.extract()

    for t in soup.find_all('table', attrs={'class': 'wikitable'}):
        print("Destroying table")
        t.decompose()
    #print("Soup Afterwards: " + str(soup))

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

    header_set = set()

    if "Wiktionary does not yet have an entry for " in str(soup):
        return "Not found."

    derivations = []
    part_of_speech = None
    one_table_found = False
    language_header, _ = get_language_header_with_soup(soup, language)
    for sibling in language_header.next_siblings:
        #print(f"Sibling: {sibling}")
        if isinstance(sibling, Tag) and sibling.get_text().strip().replace("[edit]", "") in PARTS_OF_SPEECH:
            part_of_speech = sibling.get_text().strip().replace("[edit]", "")
            print("PART OF SPEECH: " + part_of_speech)
        header = ""
        if sibling.name == 'h2':
            break
        if isinstance(sibling, Tag) and sibling.find_all('a', text="Latin correlatives"):
            print("FOUND CORRELATIVES")
            [a.decompose() for a in sibling.find_all('a', text="Latin correlatives")]
            #print("Sibling at end: " + str(sibling))
            break
        if isinstance(sibling, Tag) and sibling.has_attr('class') and sibling['class'] == "derivedterms":
            header = ""
            derived_terms = []
            for previous in sibling.previous_sibling:
                if previous.name in ['h3', 'h4']:
                    header = previous.get_text()
                    if header in header_set:
                        break
                    else:
                        header_set.add(header)
            for child in sibling.children:
                if child.name == 'ul':
                    derived_terms += [li.get_text() for li in child.find_all('li')]
                derived_terms = '\n'.join(derived_terms)
            derivations.append(f"**{header}:**\n{derived_terms.replace('Derived terms', '')}")
        else:
            if sibling.name in ['h3', 'h4', 'h5'] and sibling.get_text().strip().replace("[edit]", "") not in ['Etymology', "Etymology 1" 'Pronunciation', "Conjugation"] + PARTS_OF_SPEECH:
                header = sibling.get_text().replace("[edit]", "").strip()
                if header.lower() in ["see also", "translations"]:
                    print("FOUND TRANSLATION")
                    header = ""
                    continue
                #print("Sibling header: " + header)

                if header in PARTS_OF_SPEECH:
                    part_of_speech = header.strip()
                    print("PART OF SPEECH: " + part_of_speech)
                if re.match(r"Etymology\s[0-9]+", header):
                    continue
                if header in header_set:
                    continue
                if header in ['Declension', 'Inflection'] and language.lower() != 'latin':
                    continue
                else:
                    header_set.add(header)
                deriv_terms = []
                for sub_subling in sibling.next_siblings:
                    if isinstance(sub_subling, Tag):
                        if sub_subling.name in ['h2', 'h3', 'h4']:
                            break
                        else:
                            if header != "Declension" and header != "Inflection":
                                if header == "References":
                                    deriv_terms.append(old_dictify(sub_subling))
                                else:
                                    deriv_terms.append(sub_subling.get_text().strip())
                            else:
                                #print(sub_subling)
                                if part_of_speech in ["Noun", "Proper noun"
                                                      #,"Pronoun", "Adjective", "Participle"
                                                    ] \
                                        and language.lower() == 'latin':
                                    if not one_table_found:
                                        one_table_found = True
                                    else:
                                        continue
                                    table = sub_subling.find_next(name="table")
                                    if not table:
                                        deriv_terms.append("Table not found.")
                                        continue
                                    table_array = parse_table(table)
                                    #print(table_array)
                                    deriv_terms.append(table_array)
                                else:
                                    if "Table too large to print." not in deriv_terms:
                                        deriv_terms.append("Table too large to print.")
                deriv_terms = '\n'.join(deriv_terms)

                if header.strip() == 'Derived terms':
                    deriv_terms.replace("Derived terms", "").strip()
                derivations.append(f"**{header}:**\n{deriv_terms}")
    return '\n\n'.join(derivations).replace("Translations[edit]", "")


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
        headword_forms = [get_etymology(soup, 'Latin', headword)]
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
        headword_forms = [get_etymology(soup, 'Ancient Greek', headword)]
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
            #print("Language header: " + language_header.get_text())
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
        headword_forms = [get_etymology(soup, language.title(), headword)]
    if headword == None:
        return get_grammar_question(language, tries + 1)
    return [headword.split('•')[0].strip(), headword_forms]


def get_middle_chinese_only(soup, c):
    print("Middle Chinese only char: " + c)

    #print("Middle Chinese soup: " + str(soup))
    #matcher = r"title=\"w:Middle Chinese\">Middle Chinese</a>: <span style=\"font-size:[0-9]+%\"><span class=\"IPA\">/(.*?)/</span>"
    try:
        middle_chinese = soup.find_all("a", attrs={"title": "w:Middle Chinese"})[0].next_sibling.next_sibling.get_text().split(",")[0].replace("/", "")
    except:
        return "N/A"
    return middle_chinese

def get_old_chinese_only_zhengchang(c, soup):
    print("Old Chinese only char: " + c)
    pronunciation = ""
    try:
        pronunciation = re.findall(r"Shangfang\".*\"IPAchar\">/(.*?)/", str(soup))[0]
    except:
        traceback.print_exc()
        return "N/A"
    return pronunciation

def get_language_header(word, language):
    soup = get_soup(word)
    language_header = None
    for h2 in soup.find_all('h2'):
        # print(h2)
        if h2.span and language.title() in [s.get_text().strip() for s in h2.find_all('span')]:
            language_header = h2
            return language_header, soup
    return None, soup

def get_language_header_with_soup(soup, language):
    language_header = None
    for h2 in soup.find_all('h2'):
        # print(h2)
        if h2.span and language.title() in [s.get_text().strip() for s in h2.find_all('span')]:
            language_header = h2
            return language_header, soup
    return None, soup

def get_mandarin_pronunciation(soup):
    mandarin_pronunciation = soup.find_all('span', {'lang': 'cmn'}, recursive=True)[0].get_text()
    #mandarin_pronunciation = ''.join(re.findall(r"\(Pinyin\)\:\s*(.*?)\n", siblings))
    return mandarin_pronunciation

def get_chinese_gloss(char):
    if char in baxter_sagart.reconstructions:
        tuple_list = baxter_sagart.reconstructions[char]
        first_entry = tuple_list[0]
        pinyin, mc, oc_bax, gloss = first_entry
        return gloss
    else:
        return "gloss unavailable"

def get_historical_chinese(char):
    if char in baxter_sagart.reconstructions:
        tuple_list = baxter_sagart.reconstructions[char]
        first_entry = tuple_list[0]
        pinyin, mc, oc_bax, gloss = first_entry
        oc_bax = oc_bax.split(" (")[0].strip()
        return pinyin, mc, oc_bax
    else:
        soup = get_soup(char)
        mc = get_middle_chinese_only(soup, char)
        oc_bax = "N/A"
        return None, mc, oc_bax

def get_historical_chinese_word(word):
    language_header, soup = get_language_header(word, "Chinese")
    #print(soup)
    mandarin_word, mc_word, oc_bax_word, oc_zc_word = [], [], [], []
    for char in list(word):
        pinyin, mc, oc_bax = get_historical_chinese(char)
        mandarin_word.append(pinyin)
        mc_word.append(mc)
        oc_bax_word.append(oc_bax)
    if None in mandarin_word:
        mandarin_word = get_mandarin_pronunciation(soup)
    mc_pronunciation = "Middle Chinese: " + " ".join(mc_word).replace("/", "")
    oc_pronunciation_bax = "Old Chinese (Baxter-Sagart): " + ' '.join(oc_bax_word).replace("*", "\*")
    mandarin_pronunciation = "Mandarin: " + ''.join(mandarin_word)
    pronunciation = '\n'.join([oc_pronunciation_bax, mc_pronunciation, mandarin_pronunciation])
    return pronunciation

def get_wiktionary_glosses(soup):
    gloss_table = soup.find_all('table', attrs={'style': "clear: right;margin: 1em;border-collapse: collapse;text-align: center"})
    gloss_list = []
    if gloss_table:
        gloss_table = gloss_table[0]
        #ths = gloss_table.find_all('th', attrs={'style': "padding: 0.5em;border: 1px solid #aaa;background:#F5F5DC;font-weight: normal;font-size: 85%; width:60px"})
        char_row = gloss_table.find_all('tr')[1]
        gloss_row = gloss_table.find_all('tr')[0]
        ths = gloss_row.find_all('th')[1:]
        chars = [td.get_text().replace('\n','') for td in char_row.find_all('td')]
        print(f"WiktChars: {chars}")
        for th in ths:
            if th.find_all(attrs={'class': 'vsShow'}):
                gloss_list.append(th.find_all(attrs={'class': 'vsShow'})[0].get_text().replace('\n',''))
            else:
                gloss_list.append(th.get_text().replace('\n',''))
        print(print(f"WiktGloss: {gloss_list}"))
        gloss_tuples = list(zip(chars, gloss_list))
        return '\n'.join([f"{c}: {g}" for c, g in gloss_tuples])
    else:
        return None

def get_glyph_origin_multiple(soup, words):
    final = []
    for i, c in enumerate(words):
        if c in baxter_sagart.punctuation:
            continue
        char_soup = get_soup(c)
        print("Charlist mem: " + c)
        final.append(f"**{i+1}.** {c}: {get_glyph_origin(char_soup)}")
    return '\n\n'.join(final)

def get_glyph_origin(soup):
    origin = []
    for h in soup.find_all('h3') + soup.find_all('h4'):
        #print("H3: " + str(h3))
        if h.span and 'Glyph origin' in h.span.get_text():
            #print("In glyph origin")
            for sibling in h.next_siblings:
                if sibling.name == 'p':
                    origin.append(sibling.get_text())
                if sibling.name == 'ul':
                    origin.append(dictify(sibling))
                if sibling.name in ['h3', 'h4']:
                    break
    print("Glyph origin: " + str(origin))
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
    'Ă': 'A',
    'Ĕ': 'E',
    'Ĭ': 'I',
    'Ŏ': 'O',
    'Ŭ': 'U',
    'ă': 'a',
    'ĕ': 'e',
    'ĭ': 'i',
    'ŏ': 'o',
    'ŭ': 'u'
}

def get_japanese_pronunciation(soup):
    tokyo_pronunciations = []
    tokyo_dialect = soup.find_all(attrs={"title": "w:Tokyo dialect"})
    for pronunciation in tokyo_dialect:
        print(pronunciation)
        print(pronunciation.parent)
        surrounding = pronunciation.parent.parent
        print(surrounding)
        pronunciation = surrounding.find_all('samp', recursive=True)[0].get_text()
        tokyo_pronunciations.append(pronunciation)
    return tokyo_pronunciations

def remove_macrons(text):
    for key in mapping.keys():
        text = text.replace(key, mapping[key])
    return text
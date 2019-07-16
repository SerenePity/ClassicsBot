import unicodedata

from cltk.stem.latin.j_v import JVReplacer
from markovchain.text import MarkovText
from bs4 import BeautifulSoup
from cltk.stem.latin.declension import CollatinusDecliner
from wiktionaryparser import WiktionaryParser
import my_wiktionary_parser
import bible_versions
import old_english_bible.john
import old_english_bible.luke
import old_english_bible.mark
import old_english_bible.matthew
import romanize3
import transliteration.coptic
import transliteration.latin_antique
import transliteration.greek
import transliteration.hebrew
from mafan import simplify, tradify
from transliterate import translit, get_available_language_codes
import traceback
import requests
import json
import random
import os
import re
import string
import praw
import urllib.parse


LATIN_TEXTS_PATH = "latin_texts"
GREEK_TEXTS_PATH = "greek_texts"
OFF_TOPIC_TEXTS_PATH = "off_topic_texts"
PARALLEL_TEXTS_PATH = "parallel"
SUBREDDIT = 'copypasta'
MAX_QUOTES_LENGTH = 1000
MIN_QUOTES_LENGTH = 10
QUOTES = ["\"", "'", "“", "\""]
PRAENOMINA = ["C","L","M","P","Q","T","Ti","Sex","A","D","Cn","Sp","M","Ser","Ap","N","V", "K"]
ROMAN_NUMERALS = ["I","II","III","IV","V","VI","VII","VIII","IX","X","XI","XII","XIII","XIV","XV","XVI","XVII","XVIII","XIX","XX","XXI","XXII","XXIII","XXIV","XXV","XXVI","XXVII","XXVIII","XXIX","XXX","XXXI","XXXII","XXXIII","XXXIV","XXXV","XXXVI","XXXVII","XXXVIII","XXXIX","XL","XLI","XLII","XLIII","XLIV","XLV","XLVI","XLVII","XLVIII","XLIX","L","LI","LII","LIII","LIV","LV","LVI","LVII","LVIII","LIX","LX","LXI","LXII","LXIII","LXIV","LXV","LXVI","LXVII","LXVIII","LXIX","LXX","LXXI","LXXII","LXXIII","LXXIV","LXXV","LXXVI","LXXVII","LXXVIII","LXXIX","LXXX","LXXXI","LXXXII","LXXXIII","LXXXIV","LXXXV","LXXXVI","LXXXVII","LXXXVIII","LXXXIX","XC","XCI","XCII","XCIII","XCIV","XCV","XCVI","XCVII","XCVIII","XCIX","C","CC","CCC","CD","D","DC","DCC","DCCC","CM","M"]
ABBREVIATIONS = PRAENOMINA + [n.lower() for n in PRAENOMINA] + ["Kal", "kal", "K", "CAP", "COS", "cos", "Cos", "ann" "Mt", "mt", "viz"] + ROMAN_NUMERALS + list(string.ascii_lowercase) + list(string.ascii_uppercase)
DELIMITERS = [".", "?", "!", "...", ". . .", ".\"", "\.'", "?\"", "?'", "!\"", "!'"]
PARALLEL_DELIMITERS = ["."]
DELIMTERS_MAP = {'.': '%', '?': '#', '!': '$'}
REVERSE_DELIMITERS_MAP = {'%': '.', '#': '?', '$': '!', '^': '...'}
REGEX_SUB = re.compile(r"\[|\]|\(\)")
DELIMITERS_REGEX = "(\.\"|\.'|\.|\?|!|\^|\|)"
BIBLE_DELIMITERS = "[0-9]+"
ABSOLUTE_DELIMITER = "&%"
GETBIBLE_VERSIONS = set(['aov', 'albanian', 'amharic', 'hsab', 'arabicsv', 'peshitta', 'easternarmenian', 'westernarmenian', 'basque', 'breton', 'bulgarian1940', 'chamorro', 'cns', 'cnt', 'cus', 'cut', 'bohairic', 'coptic', 'sahidic', 'croatia', 'bkr', 'cep', 'kms', 'nkb', 'danish', 'statenvertaling', 'kjv', 'akjv', 'asv', 'basicenglish', 'douayrheims', 'wb', 'weymouth', 'web', 'ylt', 'esperanto', 'estonian', 'finnish1776', 'pyharaamattu1933', 'pyharaamattu1992', 'darby', 'ls1910', 'martin', 'ostervald', 'georgian', 'elberfelder', 'elberfelder1905', 'luther1545', 'luther1912', 'schlachter', 'gothic', 'moderngreek', 'majoritytext', 'byzantine', 'textusreceptus', 'text', 'tischendorf', 'westcotthort', 'westcott', 'lxxpar', 'lxx', 'lxxunaccentspar', 'lxxunaccents', 'aleppo', 'modernhebrew', 'bhsnovowels', 'bhs', 'wlcnovowels', 'wlc', 'codex', 'karoli', 'giovanni', 'riveduta', 'kabyle', 'korean', 'newvulgate', 'latvian', 'lithuanian', 'manxgaelic', 'maori', 'judson', 'bibelselskap', 'almeida', 'potawatomi', 'rom', 'cornilescu', 'makarij', 'synodal', 'zhuromsky', 'gaelic', 'valera', 'rv1858', 'sse', 'swahili', 'swedish', 'tagalog', 'tamajaq', 'thai', 'tnt', 'turkish', 'ukranian', 'uma', 'vietnamese', 'wolof', 'xhosa'])
COPTIC = ['bohairic', 'sahidic', 'coptic']
ARAMAIC = ['peshitta']
HEBREW = ['aleppo', 'modernhebrew', 'bhsnovowels', 'bhs', 'wlcnovowels', 'wlc', 'codex']
ARABIC = ['arabicsv']
GREEK = ['moderngreek', 'majoritytext', 'byzantine', 'textusreceptus', 'text', 'tischendorf', 'westcotthort', 'westcott', 'lxxpar', 'lxx', 'lxxunaccentspar', 'lxxunaccents']
RUSSIAN = ['makarij', 'synodal', 'zhuromsky']
GEORGIAN = ['georgian']
ARMENIAN = ['westernarmenian', 'easternarmenian']
ABSOLUTE_DELIMITER_AUTHORS = ['yogi berra', 'bush']

def format_color(text, color_type="yaml"):
    # Nothing for now
    return text + "\n"

QUOTE_RETRIEVAL_MAX_TRIES = 2

class RoboticRoman():

    def __init__(self, prefix):
        self.latin_lemmas = [w.strip() for w in open('latin_lemmas.txt').readlines()]
        self.parser = WiktionaryParser()
        self.parser.set_default_language('latin')
        self.decliner = CollatinusDecliner()
        self.quotes_dict = dict()
        self.greek_quotes_dict = dict()
        self.off_topic_quotes_dict = dict()
        self.parallel_quotes_dict = dict()
        self.markov_dict = dict()
        self.reddit = praw.Reddit(client_id=os.environ['reddit_client_id'],
                                  client_secret=os.environ['reddit_secret'],
                                  user_agent='user agent')
        self.authors = list(set([f.split('.')[0].replace('_',' ') for f in os.listdir(LATIN_TEXTS_PATH)]))
        self.greek_authors = list(set([f.split('.')[0].replace('_',' ') for f in os.listdir(GREEK_TEXTS_PATH)]))
        self.off_topic_authors = list(set([f.split('.')[0].replace('_',' ') for f in os.listdir(OFF_TOPIC_TEXTS_PATH)]))
        self.parallel_authors = list(set([f.split('.')[0].replace('_', ' ') for f in os.listdir(PARALLEL_TEXTS_PATH)]))
        self.quote_tries = 0
        self.old_english_dict = {'jn': old_english_bible.john.john, 'lk': old_english_bible.luke.luke, 'mk': old_english_bible.mark.mark, 'mt': old_english_bible.matthew.matthew}
        for author in self.authors:
            print(author)
            self.quotes_dict[author] = []

        for grecian in self.greek_authors:
            print(grecian)
            self.greek_quotes_dict[grecian] = []

        for writer in self.off_topic_authors:
            print(writer)
            self.off_topic_quotes_dict[writer] = []

        for writer in self.parallel_authors:
            print(writer)
            self.parallel_quotes_dict[writer] = []

        self.commands = [(format_color("Get random quote by author ", "CSS"), f"'{prefix}qt [-t (transliterate)] [-w[l][c] <regex search>] <author> | As <author> said:'" +
                                                                              "\n\tNotes: adding 'c' to the -w option will make your search case-sensitive, and adding 'l' will search by word lemma rather than regex."),
            (format_color("Generate markov sentence ", "CSS"),                f"'{prefix}markov [-t] <author> | As <author> allegedly said:'" +
                                                                              "\n\tNotes: -t to transliterate."),
            (format_color("List available Latin authors ", "CSS"),           f"'{prefix}latinauthors'"),
            (format_color("Retrieve random Latin quote ", "CSS"),            f"'{prefix}latinquote'"),
            (format_color("Transliterate input ", "CSS"),                    f"'{prefix}tr [-(language abbreviation)] <input>'" +
                                                                              "\n\tNotes: Greek by default, heb -> Hebrew, cop -> Coptic, unc -> Uncial, aram -> Aramaic, arab -> Arabic, syr -> Syriac, arm -> Armenian, geo -> Georgian, rus -> Russian"),
            (format_color("List Greek authors ", "CSS"),                     f"'{prefix}greekauthors'"),
            (format_color("Retrieve random Greek quote ", "CSS"),            f"'{prefix}greekquote'"),
            (format_color("Start grammar game ", "CSS"),                     f"'{prefix}<language>_game'"),
            (format_color("Start Latin grammar game ", "CSS"),               f"'{prefix}latin_grammar [-n] (no macrons)'"),
            (format_color("Start word game ", "CSS"),                        f"'{prefix}wordgame [-l <language>]'"),
            (format_color("Guess answer ", "CSS"),                           f"'<answer>' | 'g(uess) <word>'"),
            (format_color("End game ", "CSS"),                               f"'{prefix}giveup'"),
            (format_color("Join game ", "CSS"),                              f"'{prefix}join <game owner>'"),
            (format_color("Owify quote from author ", "CSS"),                f"'{prefix}owo <author>"),
            (format_color("Get available Bible versions ", "CSS"),           f"'{prefix}bibleversions [<lang>]'"),
            (format_color("Bible compare ", "CSS"),                          f"'{prefix}biblecompare [<verse>] [$]<translation1> [$]<translation2>'" +
                                                                              "\n\tNotes: add the prefix $ for transliteration."),
            (format_color("Quote for parallel text ", "CSS"),                f"'{prefix}parallel <work/author>'"),
            (format_color("Sources for parallel command ", "CSS"),           f"'{prefix}listparallel'"),
            (format_color("Word definition (defaults to Latin) ", "CSS"),    f"'{prefix}<language>_def (<word>)'"),
            (format_color("Word etymology (defaults to Latin) ", "CSS"),     f"'{prefix}<language>_ety (<word>)'"),
            (format_color("Word entry (defaults to Latin) ", "CSS"),         f"'{prefix}<language>_word (<word>)'"),
            (format_color("Random entry (defaults to Latin) ", "CSS"),       f"'{prefix}randword [<language>]' | '>randomword [<language>]'"),
            (format_color("List texts to start from an author ", "CSS"),     f"'{prefix}textstart'"),
            (format_color("Start a text from an author ", "CSS"),            f"'{prefix}pick <number>'"),
            (format_color("End text reading session ", "CSS"),               f"'{prefix}textend'"),
            (format_color("Help ", "CSS"),                                   f"'{prefix}helpme'")]

    def sort_files(self, file):
        try:
            return int(''.join([s.strip() for s in file if s.isdigit()]))
        except:
            return hash(file)

    def show_author_works(self, author, tries=0):
        if tries > 1:
            return "None found", []
        works_list = []
        file_list = []
        author = author.lower()
        if author in self.greek_authors:
            for i, file in enumerate(sorted(os.listdir(f"greek_texts/{author.replace(' ', '_')}"), key=self.sort_files)):
                if file.endswith(".txt"):
                    works_list.append(f"**{i + 1}.** {file}")
                    file_list.append(open(f"greek_texts/{author}/{file}", encoding='utf8'))
        elif author in self.authors:
            for i, file in enumerate(sorted(os.listdir(f"latin_texts/{author}"), key=self.sort_files)):
                if file.endswith(".txt"):
                    works_list.append(f"**{i + 1}.** {file}")
                    file_list.append(open(f"latin_texts/{author}/{file}", encoding='utf8'))
        elif author in self.off_topic_authors:
            for i, file in enumerate(sorted(os.listdir(f"off_topic_texts/{author}"), key=self.sort_files)):
                if file.endswith(".txt"):
                    works_list.append(f"**{i + 1}.** {file}")
                    file_list.append(open(f"off_topic_texts/{author}/{file}", encoding='utf8'))
        if len(file_list) == 0:
            return self.show_author_works('the ' + author, tries + 1)
        return '\n'.join([w.replace('.txt', '').replace('_', ' ').replace('formatted', '') for w in works_list]), file_list

    def fetch_def_by_other_parser(self, word_input, language):
        defs = []
        word = self.parser.fetch(word_input, language)
        for entry in word:
            try:
                defs.append(entry['definitions'][0]['text'])
            except:
                soup = my_wiktionary_parser.get_soup(word_input)
                print(f"https://en.wiktionary.org/wiki/{word_input}")
                defs = my_wiktionary_parser.get_definitions(soup, language)
                return defs
        if len(defs) == 0:
            # url = f"https://en.wiktionary.org/wiki/{word}"
            soup = my_wiktionary_parser.get_soup(word_input)
            defs = my_wiktionary_parser.get_definitions(soup, language)
            return defs
        return defs[0]

    def format_reconstructed(self, language, word):
        return f"Reconstruction:{language.title()}/{word}".replace('*', '')

    def get_word_defs(self, word_input, language='latin', include_examples=True):
        defs = []
        try:
            soup = my_wiktionary_parser.get_soup(word_input)
            if "Wiktionary does not yet have an entry for " in str(soup):
                return ["Not found."]
            print(f"https://en.wiktionary.org/wiki/{word_input}")
            defs = my_wiktionary_parser.get_definitions(soup, language, include_examples)
            if defs[0] == 'Not found':
                defs = self.fetch_def_by_other_parser(word_input, language)
            return defs
        except:
            defs = self.fetch_def_by_other_parser(word_input, language)
            return defs[0]
        return defs

    def word_is_in_wiktionary(self, word, language):
        url = f"https://en.wiktionary.org/wiki/{word}"
        print(url)
        print("Language: " + language)
        soup = my_wiktionary_parser.get_soup(word)
        return soup and "does not yet have an entry" not in soup

    def get_full_entry(self, word=None, language='latin'):
        print("Language: " + language)
        if not word:
            word = self.get_random_word(language)
        if language.lower() == 'chinese':
            word = tradify(word)
        soup = my_wiktionary_parser.get_soup(word)
        definition = self.get_and_format_word_defs(word, language)
        etymology = self.get_word_etymology(word, language)
        if language.lower() == 'chinese':
            word_header = self.get_word_header(word, language).strip() + "\n\n" + my_wiktionary_parser.get_middle_chinese(soup, word)
        else:
            word_header = self.get_word_header(word, language).strip()
        if 'proto' in language.lower():
            derives = self.get_derivatives(word, language, misc=False)
            return_str = f"{word_header}\n\n**Language:** {language.title()}\n\n**Definition:**\n{definition}\n\n**Etymology:**\n{etymology.strip()}\n\n{derives}"
        elif language.lower() == 'chinese':
            derives = self.get_derivatives(word, language, misc=True)
            if derives == 'Not found.':
                derives = ""
            else:
                derives = '\n\n' + derives
            #print("WORD: " + word)
            if len(list(word)) > 1:
                print("In Muliple")
                glyph_origin = my_wiktionary_parser.get_glyph_origin_multiple(list(word))
            else:
                glyph_origin = my_wiktionary_parser.get_glyph_origin(soup)
            if not glyph_origin:
                glyph_origin = "Not found."
            return_str = f"{word_header}\n\n**Language:** {language.title()}\n\n**Definition:**\n{definition}\n\n**Etymology:**\n{etymology.strip()}\n\n**Glyph Origin**\n{glyph_origin}{derives}"
        else:
            derives = self.get_derivatives(word, language, misc=True)
            if derives == 'Not found.':
                derives = ""
            else:
                derives = '\n\n' + derives
            return_str = f"{word_header}\n\n**Language:** {language.title()}\n\n**Definition:**\n{definition}\n\n**Etymology:**\n{etymology.strip()}{derives}"
            #print(return_str)
        return return_str

    def get_derivatives(self, word, language='latin', misc=False):
        soup = my_wiktionary_parser.get_soup(word)
        return my_wiktionary_parser.get_derivations(soup, language, misc)


    def get_word_header(self, word, language):
        try:
            soup = my_wiktionary_parser.get_soup(word)
            found_word = my_wiktionary_parser.get_word(soup, language, word)
        except:
            return word
        if not found_word or found_word.strip() == "":
            return word
        else:
            return found_word

    def get_word_etymology(self, word, language='latin', tries=0):
        if tries > QUOTE_RETRIEVAL_MAX_TRIES:
            return "No etymology found."
        if language.lower() == 'chinese':
            word = tradify(word)
        #word_entry = self.parser.fetch(word, language)
        etymology = None
        print("Word: " + str(word))
        try:
            soup = my_wiktionary_parser.get_soup(word)
            etymology = my_wiktionary_parser.get_etymology(soup, language).replace(u'\xa0', u' ')
            return etymology
        except:
            traceback.print_exc()
            return "Not found."

    def get_random_word(self, language='latin', tries=0, category=None):
        if tries > QUOTE_RETRIEVAL_MAX_TRIES:
            return "Could not find lemma."
        if category:
            url = f"https://en.wiktionary.org/wiki/Special:RandomInCategory/{word}"
        elif language.lower().strip() == 'latin':
            url = f"https://en.wiktionary.org/wiki/Special:RandomInCategory/Latin_terms_derived_from_Proto-Indo-European"
        elif language.lower().strip() == 'chinese':
            url = random.choice([f"https://en.wiktionary.org/wiki/Special:RandomInCategory/Middle_Chinese_lemmas",
                   "https://en.wiktionary.org/wiki/Special:RandomInCategory/Chinese_chengyu",
                   "https://en.wiktionary.org/wiki/Special:RandomInCategory/Chinese_idioms"])

        else:
            url = f"https://en.wiktionary.org/wiki/Special:RandomInCategory/{language.title()}_lemmas"
        response = requests.get(url)
        word_url = re.search(r'<link rel="canonical" href="(.*?)"/>', response.text).group(1)
        if "Reconstruction:" in word_url:
            word = word_url.split('/wiki/')[-1]
        else:
            word = urllib.parse.unquote(word_url.split('/')[-1].strip())
            if language.lower() == 'chinese':
                word = tradify(word)
        if "category:" in word.lower():
            return self.get_random_word(language, tries=tries + 1, category=word)
        etymology = self.get_word_etymology(word, language=language)
        print("Etymology in random: " + etymology)
        return urllib.parse.unquote(word).replace('_', ' ')

    def get_random_latin_lemma(self, tries=0):
        if tries > QUOTE_RETRIEVAL_MAX_TRIES:
            return "Could not find Latin lemma."
        lemma = random.choice(self.latin_lemmas)
        etymology = self.get_word_etymology(lemma)
        if not etymology or etymology.strip() == "No etymology found.":
            return self.get_random_latin_lemma(tries + 1)
        else:
            return lemma.replace('_', ' ')

    def case_transform(self, string, to_lower):
        if to_lower:
            return string.lower()
        else:
            return string

    def get_and_format_word_defs(self, word, language='latin', include_examples=True):
        if language.lower() == 'chinese':
            word = tradify(word)
        word_defs = self.get_word_defs(word, language, include_examples)
        if isinstance(word_defs, str):
            word_defs = [word_defs]
        return '\n'.join([f"{i + 1}. {e.strip()}" for i, e in enumerate(word_defs)]).replace(u'\xa0', u' ')

    def get_parallel_quote(self, author, line_num=-1):
        author = 'parallel_' + author
        if line_num < 0:
            quote = self.random_quote(author)
        else:
            f = self.parallel_quotes_dict[author.replace('parallel_', '')][0]
            try:
                quote = f.readlines()[line_num]
            except:
                f.seek(0)
                return "Line number out of range."
            f.seek(0)
        quote = quote.replace('@', '\n')
        quote = quote.replace(' () ', '\n\n')
        return quote

    def _fix_unclosed_quotes(self, text):
        opened = False
        closed = False
        quote_type = ""
        for c in text:
            if not opened and c in QUOTES:
                quote_type = c
                opened = True
            elif opened and c in QUOTES:
                closed = True
            elif closed and c in QUOTES:
                opened = True
                closed = False
        if not (open and closed):
            text += quote_type
        return text

    def _passage_parallel_deliminator(self, text, delimiters=PARALLEL_DELIMITERS):
        cur_sentence_len = 0
        prev_delimiter_pos = 0
        prev_delimiter = ""
        final_sentence = []

        for i, c in enumerate(text):
            cur_sentence_len += 1
            if c in delimiters:
                if cur_sentence_len < MIN_QUOTES_LENGTH:
                    prev_delimiter_pos = i
                    prev_delimiter = c
                    final_sentence.append(DELIMTERS_MAP[c])
                elif cur_sentence_len > MAX_QUOTES_LENGTH:
                    final_sentence.append(DELIMTERS_MAP[c])
                    final_sentence[prev_delimiter_pos] = prev_delimiter
                    prev_delimiter = c
                    prev_delimiter_pos = i
                    cur_sentence_len = i - prev_delimiter_pos
                else:
                    cur_sentence_len = 0
                    final_sentence.append(c)
            else:
                final_sentence.append(c)

        return ''.join(final_sentence)

    def _passage_deliminator(self, text, delimiters=DELIMITERS):
        cur_sentence_len = 0
        prev_delimiter_pos = 0
        prev_delimiter = ""
        final_sentence = []

        unclosed_paren = False
        for i,c in enumerate(text):
            cur_sentence_len += 1
            if c in delimiters:
                if cur_sentence_len < MIN_QUOTES_LENGTH or unclosed_paren:
                    prev_delimiter_pos = i
                    prev_delimiter = c
                    final_sentence.append(DELIMTERS_MAP[c])
                elif cur_sentence_len > MAX_QUOTES_LENGTH and not unclosed_paren:
                    final_sentence.append(DELIMTERS_MAP[c])
                    final_sentence[prev_delimiter_pos] = prev_delimiter
                    prev_delimiter = c
                    prev_delimiter_pos = i
                    cur_sentence_len = i - prev_delimiter_pos
                else:
                    cur_sentence_len = 0
                    final_sentence.append(c)
            else:
                if c == '(':
                    unclosed_paren = True
                if c == ')' and not unclosed_paren:
                    c = ''
                if c == ')' and unclosed_paren:
                    unclosed_paren = False
                final_sentence.append(c)

        return ''.join(final_sentence)

    def ulfilas_translations(self, version='kjv'):
        try:
            quote = self.random_quote('ulfilas')
            verse = re.findall(r"[0-9]*\w+\s[0-9]+:[0-9]+", quote)[0]
            book = verse.split()[0]
            while book.strip() in ['Sk', 'Sign', 'Cal']:
                quote = self.random_quote('ulfilas')
                book = quote.split()[0]
                verse = re.findall(r"[0-9]*\w+\s[0-9]+:[0-9]+", quote)[0]
            translation = verse + ' - ' + self.get_bible_verse(verse, version)
            return quote + '\n' + translation
        except Exception as e:
            traceback.print_exc()
        return "Verse not found. Please check that you have a valid Bible version by checking here https://www.biblegateway.com/versions, and here https://getbible.net/api."

    def chunks(self, lst, n):
        """Yield successive n-sized chunks from l."""
        for i in range(0, len(lst), n):
            yield lst[i:i + n]

    def get_available_bible_versions(self):
        return ', '.join(sorted([f"{key.title()}" for key in bible_versions.versions], key=str.lower))

    def get_available_bible_versions_lang(self, lang):
        versions = sorted(bible_versions.versions[lang.lower()], key=str.lower)
        return_string = f"{lang.title()}: {', '.join(versions)}"
        if len(return_string) >= 2000:
            chunks = self.chunks(versions, 10)
            return [lang.title() + ":"] + [f"{', '.join(chunk)}" for chunk in chunks]
        else:
            return [return_string]

    def reddit_quote(self, subreddit):
        subreddit_obj = self.reddit.subreddit(subreddit)
        if subreddit_obj.over18:
            return "Cannot retrieve posts from an Over 18 subreddit."
        post = subreddit_obj.random()
        if not post:
            return "This subreddit does not support random post retrieval."
        # print(post.selftext)
        if post.is_self and len(post.selftext) > 0:
            body = post.selftext
            if len(body) > 2000:
                body = body[:1995] + "..."
        elif post.url and len(post.url) > 0:
            body = post.url
        else:
            body = post.title
        return body

    def get_old_english_verse(self, verse):
        book = ''.join(verse.split(":")[0].split()[:-1]).lower()
        chapter = verse.split(':')[0].split()[-1].strip()
        verses = verse.split(':')[1].strip()
        if '-' in verses:
            begin = int(verses.replace(' ', '').split('-')[0])
            end = int(verses.replace(' ', '').split('-')[1])
            verses = [str(i) for i in range(begin, end + 1)]
        else:
            verses = [verses]

        try:
            if book in ['matthew', 'mt', 'mt.']:
                return '\n'.join([self.old_english_dict['mt'][chapter][verse].strip() for verse in verses])
            if book in ['john', 'jn', 'jn.']:
                return '\n'.join([self.old_english_dict['jn'][chapter][verse].strip() for verse in verses])
            if book in ['luke', 'lk', 'lk.']:
                return '\n'.join([self.old_english_dict['lk'][chapter][verse].strip() for verse in verses])
            if book in ['mark', 'mk', 'mk.']:
                return '\n'.join([self.old_english_dict['mk'][chapter][verse].strip() for verse in verses])
        except:
            traceback.print_exc()
            return "Not found"
        return "Not found"

    def get_bible_verse_by_api(self, verse, version='kjv'):
        url = f"https://getbible.net/json?passage={verse}&version={version}"
        book = int(verse.split(':')[0].split()[-1])
        chapters = verse.split(':')[1]
        if '-' in chapters:
            begin = int(chapters.replace(' ', '').split('-')[0])
            end = int(chapters.replace(' ', '').split('-')[1])
            chapters = [str(i) for i in range(begin, end + 1)]
        else:
            chapters = [chapters]
        response = requests.get(url).text.replace(');', '').replace('(', '')
        content = json.loads(response)
        verses = []
        try:
            for chapter in chapters:
                verses.append(content['book'][0]['chapter'][chapter]['verse'].replace('\n', ''))
            passage = ' '.join(verses)
        except:
            passage = "Not found"
            traceback.print_exc()
        if version.strip().lower() == 'gothic':
            passage = re.sub(r"\[\w+\]\s", '', passage)
        if not passage or len(passage.strip()) == 0:
            passage = "Not found"
        return passage

    def get_bible_verse_from_gateway(self, verse, version='kjv'):
        url = f"https://www.biblegateway.com/passage/?search={verse}&version={version}&src=tools"
        response = requests.get(url)
        try:
            soup = BeautifulSoup(response.text)
            passage = soup.find('div', {'class': 'result-text-style-normal'})
            if passage.h1:
                passage.h1.extract()
            if passage.h2:
                passage.h2.extract()
            if passage.h3:
                passage.h3.extract()
            cross_refs = passage.find('div', {'class': 'crossrefs'})
            if cross_refs:
                passage.find('div', {'class': 'crossrefs'}).extract()
            footnotes = passage.find('div', {'class': 'footnotes'})
            if footnotes:
                passage.find('div', {'class': 'footnotes'}).extract()
            passage = passage.get_text()
            passage = re.sub(r"^\s*[0-9]+\s*", "", passage)
            passage = re.sub(r"\s*[0-9]+\s*", "\n", passage)
            passage = re.sub(r"[\s]{2,}", "\n", passage)
            passage = re.sub(r"[0-9]+(\w)", "\1", passage)
        except:
            passage = "Not found"
        return passage.replace('\t', ' ')

    def get_wycliffe_verse(self, verse):
        url = f"https://studybible.info/Wycliffe/{verse}"
        body = requests.get(url).text
        soup = BeautifulSoup(body)
        passage = soup.find_all("div", {"class": "passage row Wycliffe"})[0]
        [s.extract() for s in soup('sup')]
        return re.sub(r"[\s]{2,}", "\n", passage.get_text().replace('Wycliffe', '').strip())

    def get_bible_verse(self, verse, version='kjv'):
        translit = False
        if version[0] == '$':
            version = version[1:]
            translit = True
        verse = verse.title()
        passage = "Not found"
        if version.strip().lower() == 'wyc':
            try:
                return self.get_wycliffe_verse(verse)
            except:
                traceback.print_exc()
                return "Not found"
        if version.strip().lower() == 'old_english':
            try:
                return self.get_old_english_verse(verse)
            except:
                traceback.print_exc()
                return "Not found"
        if version.strip().lower() == 'gothic':
            try:
                passage = self.get_gothic_passage(verse.title())
                return passage
            except:
                passage = self.get_bible_verse_by_api(verse, version)
                traceback.print_exc()
        try:
            if version.strip().lower() in GETBIBLE_VERSIONS:
                try:
                    passage = self.get_bible_verse_by_api(verse, version)
                except:
                    passage = self.get_bible_verse_from_gateway(verse, version)
                if passage == 'Not found':
                    try:
                        passage = self.get_bible_verse_from_gateway(verse, version)
                    except:
                        passage = "Not found"
            else:
                passage = self.get_bible_verse_from_gateway(verse, version)
            if translit:
                passage = self.transliterate_verse(version, passage)
        except:
            traceback.print_exc()
            passage = "Not found"
        return passage.strip()

    def get_random_verse_by_testament(self, testament):
        verses = open(f"bible_verses_{testament}.txt").read().split('|')
        return random.choice(verses).title()

    def get_gothic_verses_set(self):
        text = open('off_topic_texts/ulfilas/gothic_bible.txt', encoding='utf8').read()
        return set([v.lower() for v in re.findall(r"\w+\s[0-9]+:[0-9]+", text)])

    def get_old_english_verses_set(self):
        final = []
        for book in self.old_english_dict.keys():
            chapters = self.old_english_dict[book].keys()
            for chapter in chapters:
                verses = self.old_english_dict[book][chapter].keys()
                for verse in verses:
                    final.append(f"{book} {chapter}:{verse}")
        return set(final)

    def get_random_verse(self):
        verses = open(f"bible_verses.txt").read().split('|')
        return random.choice(verses).title()

    def bible_compare_random_verses(self, versions: list):
        versions = [version.strip().lower() for version in versions]
        if 'gothic' in versions:
            verse = self.get_gothic_verse()
        elif 'old_english' in versions:
            book = random.choice(['jn', 'lk', 'mk', 'mt'])
            oe_dict = self.old_english_dict[book]
            chapter = random.choice(list(oe_dict.keys()))
            verse = random.choice(list(oe_dict[chapter].keys()))
            verse = f"{book} {chapter}:{verse}"
        elif 'gothic' in versions and 'old_english' in versions:
            gothic_verses = self.get_gothic_verses_set()
            oe_verses = self.get_old_english_verses_set()
            intersection = gothic_verses.intersection(oe_verses)
            verse = random.choice(list(intersection))
        else:
            verse = self.get_random_verse()
        try:
            translations = [f"**{verse.title()}** - {self.get_bible_verse(verse, version)}" for version in versions]
            if "Not found" in ' '.join([t.split(' - ')[1].strip() for t in translations]):
                verse = self.get_random_verse_by_testament("nt")
                translations = [f"**{verse.title()}** - {self.get_bible_verse(verse, version)}" for version in versions]
                if "Not found" in ' '.join([t.split(' - ')[1].strip() for t in translations]):
                    verse = self.get_random_verse_by_testament("ot")
                    translations = [f"**{verse.title()}** - {self.get_bible_verse(verse, version)}" for version in
                                    versions]
        except:
            verse = self.get_random_verse_by_testament("nt")
            try:
                translations = [f"**{verse.title()}** - {self.get_bible_verse(verse, version)}" for version in versions]
            except:
                try:
                    verse = self.get_random_verse_by_testament("ot")
                    translations = [f"**{verse.title()}** - {self.get_bible_verse(verse, version)}" for version in
                                    versions]
                except:
                    return "Failed to retrieve verse. Your target versions may be incompatible. For example, the Gothic Bible contains only the New Testament, while the Westminster Leningrad Codex contains only the Old Testament. There will be no overlapping verses."

        return '\n'.join(translations)

    def transliterate_verse(self, version, text):
        if version in COPTIC:
            return transliteration.coptic.transliterate(text).lower()
        if version in ARAMAIC:
            r = romanize3.__dict__['syc']
            return r.convert(text)
        if version in HEBREW:
            return transliteration.hebrew.transliterate(text).lower()
        if version in ARABIC:
            r = romanize3.__dict__['ara']
            return r.convert(text)
        if version in GREEK:
            return transliteration.greek.transliterate(text)
        if version in RUSSIAN:
            return text
        if version in ARMENIAN:
            return translit(input, 'hy', reversed=True).replace('ւ', 'v')
        if version in GEORGIAN:
            return translit(input, 'ka', reversed=True).replace('ჲ', 'y')
        if version == "uncial":
            return transliteration.latin_antique(text)
        return text

    def bible_compare(self, verse, versions: list):
        try:
            translations = [f"**{verse.title()}** - {self.get_bible_verse(verse, version)}" for version in versions]
        except:
            return "Failed to retrieve verse. One of your target versions may not contain the requested verse. For example, the Gothic Bible only contains the New Testament, and so requesting an Old Testament verse will fail."
        return '\n'.join(translations)

    def get_gothic_verse(self):
        try:
            quote = self.random_quote('ulfilas')
            verse = re.findall(r"[0-9]*\w+\s[0-9]+:[0-9]+", quote)[0]
            book = verse.split()[0]
            while book.strip() in ['Sk', 'Sign', 'Cal']:
                quote = self.random_quote('ulfilas')
                book = quote.split()[0]
                verse = re.findall(r"[0-9]*\w+\s[0-9]+:[0-9]+", quote)[0]
            return verse
        except Exception as e:
            traceback.print_exc()
        return None

    def get_gothic_passage(self, verse):
        text = open('off_topic_texts/ulfilas/gothic_bible.txt', encoding='utf8').read()
        return re.findall(f"{verse} - (.*?)\|", text)[0]

    def bible_compare_random(self, versions: list):
        if 'gothic' in [version.strip().lower() for version in versions]:
            verse = self.get_gothic_verse()
        else:
            verse = self.get_random_verse()
        return self.bible_compare(verse, versions)

    def _replace_placeholders(self, text):
        for key in REVERSE_DELIMITERS_MAP:
            text = text.replace(key, REVERSE_DELIMITERS_MAP[key])
        return text

    def _process_basic(self, text):
        return ['. '.join(s) + '.' for s in list(self.chunks(text.split('.'), 3))]

    def _process_absolute(self, text):
        return text.split(ABSOLUTE_DELIMITER)

    def _process_text(self, text):
        text = self._replace_abbreviation_period(text.replace('...', '^'))
        text = self._passage_deliminator(text)
        text = re.sub(r"[\n]{2,}|(\n+\s+){2,}|(\s+\n+){2,}", "\n\n", text)
        first_pass = [s for s in re.split(DELIMITERS_REGEX, text)]
        return [re.sub(REGEX_SUB, '', t) + (first_pass[i+1] if first_pass[i+1] != '|' else '') for i,t in
                enumerate(first_pass) if 'LIBRARY' not in t.upper()
                and t.strip().replace('\n','') != '' and MIN_QUOTES_LENGTH < len(t) < MAX_QUOTES_LENGTH and
                i < len(first_pass) - 1]

    def _process_parallel(self, text):
        text = self._replace_abbreviation_period(text.replace('...', '^'))
        text = self._passage_parallel_deliminator(text, delimiters=PARALLEL_DELIMITERS)
        text_list = text.split('\n')
        # text_list = [t.replace('@', '\n') for t in text_list]
        return text_list

    def _process_holy_text(self, scripture):
        return [s for s in re.split(BIBLE_DELIMITERS, self._replace_abbreviation_period(scripture))
                if 'LATIN' not in s.upper() and 'LIBRARY' not in s.upper() and s.strip().replace('\n', '') != ''
                and MIN_QUOTES_LENGTH < len(s) < MAX_QUOTES_LENGTH]

    def _replace_abbreviation_period(self, text):
        for abbreviations in ABBREVIATIONS:
            text = text.replace(" " + abbreviations + '.', " " + abbreviations + '%')
        return text

    def load_all_models(self):
        for author in self.authors:
            self.load_quotes(author)

        for grecian in self.greek_quotes_dict:
            print(grecian)
            self.load_greek_quotes(grecian)

        for person in self.off_topic_quotes_dict:
            print(person)
            print(person)
            self.load_off_topic_quotes(person)

        for person in self.parallel_quotes_dict:
            print(person)
            self.load_parallel_quotes(person)

        print("Finished loading models")

    """
    def load_markov_model(self, author):
        try:
            self.markov_dict[author] = f"markov_models/{author}/{author}_markov.json"
        except:
            self.load_model(author)
            self.markov_dict[author] = f"markov_models/{author}/{author}_markov.json"
    """

    def load_greek_quotes(self, author):
        author_dir = author.replace(' ', '_')
        author_path = f"{GREEK_TEXTS_PATH}/{author_dir}/"
        for file in os.listdir(author_path):
            if file.endswith('.txt'):
                self.greek_quotes_dict[author].append(open(f"{author_path}/{file}", encoding='utf8'))

    def load_quotes(self, author):
        self.quotes_dict[author] = []
        author_path = f"{LATIN_TEXTS_PATH}/{author}/"
        for file in os.listdir(author_path):
            if file.endswith('.txt'):
                self.quotes_dict[author].append(open(f"{author_path}/{file}", encoding='utf8'))

    def load_off_topic_quotes(self, author):
        self.off_topic_quotes_dict[author] = []
        author_path = f"{OFF_TOPIC_TEXTS_PATH}/{author}/"
        for file in os.listdir(author_path):
            if file.endswith('.txt'):
                self.off_topic_quotes_dict[author].append(open(f"{author_path}/{file}", encoding='utf8'))

    def load_parallel_quotes(self, author):
        self.parallel_quotes_dict[author] = []
        author_path = f"{PARALLEL_TEXTS_PATH}/{author}/"
        for file in os.listdir(author_path):
            if file.endswith('.txt'):
                self.parallel_quotes_dict[author].append(open(f"{author_path}/{file}", encoding='utf8'))

    def format_name(self, author):
        return author.title().replace('Of ', 'of ').replace('The ', 'the ').replace(' De ',
                                                                        ' de ')
    def pick_random_quote(self):
        author = random.choice(list(self.quotes_dict.keys()))
        return f"{self.random_quote(author)[1]}\n\t―{self.format_name(author)}"

    def flatten(self, array):
        return [item for sublist in array for item in sublist]

    def find_multi_regex(self, regexes, passage, case_sensitive):
        if not case_sensitive:
            passage = passage.lower()
        generic_re = re.compile('|'.join(regexes))
        matches = re.findall(generic_re, passage)
        if matches and len(matches) > 0:
            return matches[0]
        else:
            return None

    def matching_quote(self, file, regex, case_sensitive, proces_func):
        quotes = []
        for i, quote in enumerate(file.read()):
            quotes.append(quote)
            return i, quotes, self.find_multi_regex(regex, re.sub(r"[^\w0-9\s\n]", "", proces_func(quote), case_sensitive))

    def unpack(self, *lst):
        return lst

    def remove_accents(self, input_str):
        if isinstance(input_str, bytes) or isinstance(input_str, bytearray):
            input_str = input_str.decode('utf8')
        nfkd_form = unicodedata.normalize('NFKD', input_str)
        return u"".join([c for c in nfkd_form if not unicodedata.combining(c)])

    def pick_quote(self, files, process_func, word=None, lemmatize=False, case_sensitive=False, tries=0):
        # print(', '.join([f.name for f in files]))
        if tries > 2:
            return -1, "Not found.", []
        if word:
            word = self.remove_accents(word).lower() if not case_sensitive else word
            regex_list = []
            if lemmatize:
                try:
                    #words = self.flatten([[f"{word} ", f" {word} ", f" {word}."] for word in self.decliner.decline(word, flatten=True)])
                    inflected = self.decliner.decline(word, flatten=True)
                    for form in inflected:
                        regex_list.append(f"\\b{form}\\b")
                except:
                    traceback.print_exc()
                    return -1, "Unknown lemma.", []
            else:
                #words = ['|'.join([f"(^{word}\\b+?)", f"(\\b{word}\\b+?)", f"(\\b{word}\\.)"])]
                #words = [f"{word} ", f" {word} ", f" {word}."]
                regex_list.append(f"\\b{word}\\b")
                # words = [r"(\s" + word + r"\s|^" + word + r"|\s" + word + r"\.)"]
            print(regex_list)
            search_quotes = []
            quotes_list = []
            all_quotes = []
            for f in files:
                # print([re.sub(r"[^a-z0-9\s\n]", "", p.lower()) for p in process_func(f.read())])
                for p in process_func(f.read()):
                    search_target = self.find_multi_regex(regex_list, re.sub(r"[^\w0-9\s\n]", "", self.remove_accents(p)), case_sensitive)
                    if search_target:
                        search_quotes.append(p)
                        quotes_list.append(p + "_found")
                    else:
                        quotes_list.append(p)
                quotes_list.append("--------------------------EOF--------------------------")
                f.seek(0)
            if len(search_quotes) == 0:
                print("Search_quotes is 0")
                j = JVReplacer()
                index, quote, quotes_list = self.pick_quote(files, process_func, j.replace(word), lemmatize, case_sensitive,  tries + 1)
                if not search_quotes or len(search_quotes) == 0:
                    return -1, "Not found.", []
            else:
                return_values = []
                for i, quote in enumerate(quotes_list):
                    if quote.endswith("_found"):
                        return_values.append((i, quote.replace("_found", ""),  quotes_list))
                ret = random.choice(return_values)
                #print("Return: " + str(ret))
                return ret[0], ret[1], ret[2]
        else:
            f = random.choice(files)
            quotes_list = process_func(f.read())
            index = random.randint(0, len(quotes_list))
            quote = quotes_list[index]
            f.seek(0)
        return index, quote, quotes_list

    def get_passage_list_for_file(self, file, process_func):
        return process_func(file.read())

    def get_text_list_for_person(self, person):
        if person in self.greek_quotes_dict:
            files = self.greek_quotes_dict[person]
        elif "the " + person in self.greek_quotes_dict:
            files = self.greek_quotes_dict["the " + person]
        elif person in self.off_topic_authors:
            files = self.off_topic_quotes_dict[person]
        elif 'the ' + person in self.off_topic_authors:
            files = self.off_topic_quotes_dict['the ' + person]
        elif 'parallel_' in person:
            files = self.parallel_quotes_dict[person.replace('parallel_', '')]
        else:
            if not person in self.quotes_dict:
                person = "the " + person
            files = self.quotes_dict[person]
        file = random.choice(files).read()
        if person == 'the bible':
            return re.split(BIBLE_DELIMITERS, file)
        return file.split('.')

    def get_quote_list(self, person, word, lemmatize=False, case_sensitive=False):
        print(person)
        if person.strip().lower() == 'reddit':
            return self.reddit_quote(SUBREDDIT)
        if person in self.greek_quotes_dict:
            files = self.greek_quotes_dict[person]
            try:
                i, quote = self.pick_quote(files, self._process_text, word, lemmatize, case_sensitive)
            except Exception as error:
                if self.quote_tries < QUOTE_RETRIEVAL_MAX_TRIES:
                    self.quote_tries += 1
                    i, quote = self.pick_quote(files, self._process_text, word, lemmatize, case_sensitive)
                    return quote
                else:
                    self.quote_tries = 0
                    raise error
        elif "the " + person in self.greek_quotes_dict:
            files = self.greek_quotes_dict["the " + person]
            try:
                i, quote = self.pick_quote(files, self._process_text, word, lemmatize, case_sensitive)
            except Exception as error:
                if self.quote_tries < QUOTE_RETRIEVAL_MAX_TRIES:
                    self.quote_tries += 1
                    i, quote = self.pick_quote(files, self._process_text, word, lemmatize, case_sensitive)
                    return i, quote
                else:
                    self.quote_tries = 0
                    raise error
        elif person in self.off_topic_authors:
            files = self.off_topic_quotes_dict[person]
            if person.lower() == "joyce":
                quote = self.pick_quote(files, self._process_basic, word, lemmatize, case_sensitive)
            elif person.lower() == "bush" or person.lower() == "yogi berra":
                i, quote = self.pick_quote(files, self._process_absolute, word, lemmatize, case_sensitive)
                print(quote)
            else:
                i, quote = self.pick_quote(files, self._process_basic, word, lemmatize, case_sensitive)
        elif 'the ' + person in self.off_topic_authors:
            files = self.off_topic_quotes_dict['the ' + person]
            i, quote = self.pick_quote(files, self._process_text, word, lemmatize, case_sensitive)
        elif 'parallel_' in person:
            files = self.parallel_quotes_dict[person.replace('parallel_', '')]
            i, quote = self.pick_quote(files, self._process_parallel, word, lemmatize, case_sensitive)
            print("Parallel quote: " + quote)
        else:
            if not person in self.quotes_dict:
                person = "the " + person
            files = self.quotes_dict[person]
            if person == 'the bible':
                i, quote = self.pick_quote(files, self._process_holy_text, word, lemmatize, case_sensitive)
            else:
                i, quote = self.pick_quote(files, self._process_text, word, lemmatize, case_sensitive)
        return re.sub(r"^[\s]*[\n]+[\s]*", " ", self.fix_crushed_punctuation(self._replace_placeholders(quote)))

    def random_quote(self, person, word=None, lemmatize=False, case_sensitive=False):
        print(person)
        if person.strip().lower() == 'reddit':
            return self.reddit_quote(SUBREDDIT)
        if person in self.greek_quotes_dict:
            files = self.greek_quotes_dict[person]
            try:
               i, quote, quotes_list = self.pick_quote(files, self._process_text, word, lemmatize, case_sensitive)
            except Exception as error:
                if self.quote_tries < QUOTE_RETRIEVAL_MAX_TRIES:
                    self.quote_tries += 1
                    i, quote, quotes_list = self.pick_quote(files, self._process_text, word, lemmatize, case_sensitive)
                    return i, quote, quotes_list
                else:
                    self.quote_tries = 0
                    raise error
        elif "the " + person in self.greek_quotes_dict:
            files = self.greek_quotes_dict["the " + person]
            try:
                i, quote, quotes_list = self.pick_quote(files, self._process_text, word, lemmatize, case_sensitive)
            except Exception as error:
                if self.quote_tries < QUOTE_RETRIEVAL_MAX_TRIES:
                    self.quote_tries += 1
                    i, quote, quotes_list = self.pick_quote(files, self._process_text, word, lemmatize, case_sensitive)
                    return i, quote
                else:
                    self.quote_tries = 0
                    raise error
        elif person in self.off_topic_authors:
            files = self.off_topic_quotes_dict[person]
            if person.lower() == "joyce":
                i, quote, quotes_list = self.pick_quote(files, self._process_basic, word, lemmatize, case_sensitive)
            elif person.lower() == "bush" or person.lower() == "yogi berra":
                i, quote, quotes_list = self.pick_quote(files, self._process_absolute, word, lemmatize, case_sensitive)
                print(quote)
            else:
                i, quote, quotes_list = self.pick_quote(files, self._process_text, word, lemmatize, case_sensitive)
        elif 'the ' + person in self.off_topic_authors:
            files = self.off_topic_quotes_dict['the ' + person]
            i, quote, quotes_list = self.pick_quote(files, self._process_text, word, lemmatize, case_sensitive)
        elif 'parallel_' in person:
            files = self.parallel_quotes_dict[person.replace('parallel_', '')]
            i, quote, quotes_list = self.pick_quote(files, self._process_parallel, word, lemmatize, case_sensitive)
            print("Parallel quote: " + quote)
        else:
            if not person in self.quotes_dict:
                person = "the " + person
            files = self.quotes_dict[person]
            if person == 'the bible':
                i, quote, quotes_list = self.pick_quote(files, self._process_holy_text, word, lemmatize, case_sensitive)
            else:
                i, quote, quotes_list = self.pick_quote(files, self._process_text, word, lemmatize, case_sensitive)
        return i, re.sub(r"^[\s]*[\n]+[\s]*", " ", self.sanitize(quote)), quotes_list

    def sanitize(self, quote):
        return self.fix_crushed_punctuation(self._replace_placeholders(quote))

    def fix_crushed_punctuation(self, text):
        text = re.sub(r"(\w)\.([^\s])", r"\1. \2", text)
        text = re.sub(r"(\w);([^\s])", r"\1; \2", text)
        text = re.sub(r"(\w)\?([^\s])", r"\1? \2", text)
        text = re.sub(r"(\w)!([^\s])", r"\1! \2", text)
        return text

    def pick_greek_quote(self):
        author = random.choice(list(self.greek_quotes_dict.keys()))
        return f"{self.random_quote(author)[1]}\n\t―{self.format_name(author)}"

    def load_model(self, author):
        return MarkovText.from_file(f"markov_models/{author}/{author}_markov.json")

    def make_sentence(self, author):
        if author.strip().lower() == 'reddit':
            return "Just to be clear, I'm not a professional \"quote maker\". I'm just an atheist teenager who greatly " \
                   "values his intelligence and scientific fact over any silly fiction book written 3,500 years ago. " \
                   "That being said, I am open to any and all criticism.\n\n\"In this moment, I am euphoric. " \
                   "Not because of any phony god's blessing. But because, I am englightened by my intelligence.\" - Aalewis"
        if not os.path.isfile(f"markov_models/{author}/{author}_markov.json"):
            if author in self.authors:
                path = f"{LATIN_TEXTS_PATH}/{author}"
            elif author in self.greek_authors:
                path = f"{GREEK_TEXTS_PATH}/{author}"
            else:
                path = f"{OFF_TOPIC_TEXTS_PATH}/{author}"
            self.train_model(author, path)
        return self.fix_crushed_punctuation(self.load_model(author)(max_length=MAX_QUOTES_LENGTH))

    def train_model(self, author, author_path):
        model = MarkovText()
        for file in os.listdir(author_path):
            with open(author_path + '/' + file, encoding="utf8") as fp:
                model.data(fp.read())
        if not os.path.exists(f"markov_models/{author}"):
            os.mkdir(f"markov_models/{author}")
        model.save(f"markov_models/{author}/{author}_markov.json")

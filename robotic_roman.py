import unicodedata
from functools import reduce

from bs4 import BeautifulSoup, Tag
from wiktionaryparser import WiktionaryParser
from latin_word_picker import word_picker
import my_wiktionary_parser
import bible_versions
import old_english_bible.john
import old_english_bible.luke
import old_english_bible.mark
import old_english_bible.matthew
import romanize3
from lang_trans.arabic import arabtex
import transliteration.coptic
import transliteration.latin_antique
import transliteration.greek
import transliteration.hebrew
import transliteration.mandarin
import transliteration.middle_chinese
import transliteration.korean
from mafan import tradify
from transliterate import translit
import traceback
import requests
import json
import random
import os
import re
import string
import urllib.parse
import roman
from get_cc_passage import get_cc_verse

# Relative paths to files containing source texts
LATIN_TEXTS_PATH = "latin_texts"
GREEK_TEXTS_PATH = "greek_texts"
CHINESE_TEXTS_PATH = "chinese_texts"
GERMANIC_TEXTS_PATH = "germanic_texts"
PARALLEL_TEXTS_PATH = "parallel"

# Default subreddit for reddit shenanigans
SUBREDDIT = 'copypasta'

# Maximum length of quote (counted in characters) from any given text
MAX_QUOTES_LENGTH = 1000

# Minimum length of quote retrieved from a given text
MIN_QUOTES_LENGTH = 50

# Different quotation marks used in various languages. Useful for sentence delimination.
QUOTES = ["\"", "'", "“", "\"", "」", "「"]

# List of abbreviated Roman praenomina, which often end with a period, which can artificially cut short a sentence.
PRAENOMINA = ["C", "L", "M", "P", "Q", "T", "Ti", "Sex", "A", "D", "Cn", "Sp", "M", "Ser", "Ap", "N", "V", "K"]

# Roman numerals also often end with a period, and must be dealt with in the like manner.
ROMAN_NUMERALS = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI", "XII", "XIII", "XIV", "XV", "XVI",
                  "XVII", "XVIII", "XIX", "XX", "XXI", "XXII", "XXIII", "XXIV", "XXV", "XXVI", "XXVII", "XXVIII",
                  "XXIX", "XXX", "XXXI", "XXXII", "XXXIII", "XXXIV", "XXXV", "XXXVI", "XXXVII", "XXXVIII", "XXXIX",
                  "XL", "XLI", "XLII", "XLIII", "XLIV", "XLV", "XLVI", "XLVII", "XLVIII", "XLIX", "L", "LI", "LII",
                  "LIII", "LIV", "LV", "LVI", "LVII", "LVIII", "LIX", "LX", "LXI", "LXII", "LXIII", "LXIV", "LXV",
                  "LXVI", "LXVII", "LXVIII", "LXIX", "LXX", "LXXI", "LXXII", "LXXIII", "LXXIV", "LXXV", "LXXVI",
                  "LXXVII", "LXXVIII", "LXXIX", "LXXX", "LXXXI", "LXXXII", "LXXXIII", "LXXXIV", "LXXXV", "LXXXVI",
                  "LXXXVII", "LXXXVIII", "LXXXIX", "XC", "XCI", "XCII", "XCIII", "XCIV", "XCV", "XCVI", "XCVII",
                  "XCVIII", "XCIX", "C", "CC", "CCC", "CD", "D", "DC", "DCC", "DCCC", "CM", "M"]

# Roman praenomina, Roman numerals, and other common abbreviations that can interfere with proper sentence segmentation.
ABBREVIATIONS = PRAENOMINA + [n.lower() for n in PRAENOMINA] + ["Kal", "kal", "K", "CAP", "COS", "cos", "Cos",
                                                                "ann" "Mt", "mt", "viz", 'mss', 'MSS', "Dr", "dr", "Mr",
                                                                "mr", "Mrs", "mrs", "Ms", "ms", "St",
                                                                "st"] + ROMAN_NUMERALS + list(
    string.ascii_lowercase) + list(string.ascii_uppercase)

# Unused at the moment
PARALLEL_DELIMITERS = ["."]

""" List of sentence delimiters (such as periods, question marks, exclamation points, and other punctuation found in other 
languages), mapped to placeholder delimiters so that that sentences below the minimum quote-length threshold can be added 
to the following sentence (since two-word sentences are not very interesting"""
DELIMTERS_MAP = {'.': '%', '?': '#', '!': '$', '。': '¡', '！': '±', '？': '∓', '‰': '\n'}

# Reverse delimiter map to map the temporary sentence pseudo-delimiters back to their original characters in the final output
REVERSE_DELIMITERS_MAP = {'%': '.', '#': '?', '$': '!', '^': '...', '¡': '。', '±': '！', '∓': '？', '‰': '\n'}

# Regex expression of characters that need to be exterminated with extreme prejudice
REGEX_SUB = re.compile(r"\[|\]|\(\)")

# Regex listing sentence deliminators
DELIMITERS_REGEX = "(\.\"|\.'|\.|\?|!|\^|\||。|！|？|。」|！」|？」)"

# Special deliminators for the Bible
BIBLE_DELIMITERS = "[0-9\.?!\n]+[^:]"

# NOT_BIBLE_DELIMITERS = "[^0-9\.?!]+"
# BIBLE_DELIMITERS = " ([0-9\.?!]+)"

# Special deliminator that I occasionally manually insert into texts to force sentence or paragraph breaks
ABSOLUTE_DELIMITER = "‰"

# List of delimiters
DELIMITERS = [".", "?", "!", "...", ". . .", ".\"", "\.'", "?\"", "?'", "!\"", "!'", "。", "！", "？", ABSOLUTE_DELIMITER]

# List of Bible versions in all languages
GETBIBLE_VERSIONS = {'aov', 'albanian', 'amharic', 'hsab', 'arabicsv', 'peshitta', 'easternarmenian', 'westernarmenian',
                     'basque', 'breton', 'bulgarian1940', 'chamorro', 'cns', 'cnt', 'cus', 'cut', 'bohairic', 'coptic',
                     'sahidic', 'croatia', 'bkr', 'cep', 'kms', 'nkb', 'danish', 'statenvertaling', 'kjv', 'akjv',
                     'asv', 'basicenglish', 'douayrheims', 'wb', 'weymouth', 'web', 'ylt', 'esperanto', 'estonian',
                     'finnish1776', 'pyharaamattu1933', 'pyharaamattu1992', 'darby', 'ls1910', 'martin', 'ostervald',
                     'georgian', 'elberfelder', 'elberfelder1905', 'luther1545', 'luther1912', 'schlachter', 'gothic',
                     'moderngreek', 'majoritytext', 'byzantine', 'textusreceptus', 'text', 'tischendorf',
                     'westcotthort', 'westcott', 'lxxpar', 'lxx', 'lxxunaccentspar', 'lxxunaccents', 'aleppo',
                     'modernhebrew', 'bhsnovowels', 'bhs', 'wlcnovowels', 'wlc', 'codex', 'karoli', 'giovanni',
                     'riveduta', 'kabyle', 'korean', 'newvulgate', 'latvian', 'lithuanian', 'manxgaelic', 'maori',
                     'judson', 'bibelselskap', 'almeida', 'potawatomi', 'rom', 'cornilescu', 'makarij', 'synodal',
                     'zhuromsky', 'gaelic', 'valera', 'rv1858', 'sse', 'swahili', 'swedish', 'tagalog', 'tamajaq',
                     'thai', 'tnt', 'turkish', 'ukranian', 'uma', 'vietnamese', 'wolof', 'xhosa', 'nav', 'erv-ar'}

# The below are versions of the Bible (some being exclusively New Testament for a variety of language to support my parallel Bible text module
COPTIC = ['bohairic', 'sahidic', 'coptic']
ARAMAIC = ['peshitta']
HEBREW = ['aleppo', 'modernhebrew', 'bhsnovowels', 'bhs', 'wlcnovowels', 'wlc', 'codex']
ARABIC = ['arabicsv', 'nav', 'erv-ar']
GREEK = ['moderngreek', 'majoritytext', 'byzantine', 'textusreceptus', 'text', 'tischendorf', 'westcotthort',
         'westcott', 'lxxpar', 'lxx', 'lxxunaccentspar', 'lxxunaccents', 'sblgnt']
RUSSIAN = ['makarij', 'synodal', 'zhuromsky']
UKRAINIAN = ['ukr', 'ukrainian', 'ukr-uk']
BULGARIAN = ['bg1940', 'bulgarian1940', 'bulg', 'erv-bg']
SERBIAN = ['erv-sr']
GEORGIAN = ['georgian']
ARMENIAN = ['westernarmenian', 'easternarmenian']
KOREAN = ['korean', 'klb']
CHINESE = ['ccb', 'ccbt', 'erv-zh', 'cns', 'cnt', 'cus', 'cut']

# Authors for whom the primary delimiter is the 'absolute delimiter' mentioned above
ABSOLUTE_DELIMITER_AUTHORS = ['yogi berra', 'bush', 'phrases']


# Does nothing at the moment. May be useful when Discord has better color support
def format_color(text, color_type="yaml"):
    # Nothing for now
    return text + "\n"


QUOTE_RETRIEVAL_MAX_TRIES = 2


class QuoteContext():
    """
    Models the context of a quote--the quote itself, as well as the sentences before and after it.
    """

    def __init__(self, author, quotes, index, works_list):
        self.author = author
        self.quotes = quotes
        self.index = index
        self.before_index = index
        self.after_index = index
        self.works_list = works_list
        self.first_before = True

    def get_surrounding(self, before=None, after=None, joiner='.', tries=0):
        if tries > 1:
            return "Not found."
        quotes_list = []
        if before and after:
            if self.index > len(self.quotes) - 1:
                self.index = len(self.quotes) - 1
            self.before_index = max(0, self.index - before - 1)
            self.after_index = min(len(self.quotes), self.index + after)
            print("Center: " + self.quotes[self.index])
            quotes_list = self.quotes[self.before_index:self.after_index]
        elif before:
            try:
                if self.first_before:
                    self.first_before = False
                    self.before_index = max(0, self.index - before)
                    quotes_list = self.quotes[self.before_index:self.index][1:]
                    self.index = self.before_index
            except:
                quotes_list = self.get_surrounding(before=before)
            self.before_index = self.index - before
            quotes_list = self.quotes[self.before_index:self.index]
            self.index = self.before_index
            if quotes_list == []:
                quotes_list = self.get_surrounding(before=before, tries=tries + 1)
        elif after:
            old_after = self.after_index
            if self.after_index == len(self.quotes):
                return "Text ended"
            if self.after_index + after > len(self.quotes) - 1:
                self.after_index = len(self.quotes)
            else:
                self.after_index = self.after_index + after
                print("After index: " + str(self.after_index))
            quotes_list = self.quotes[old_after:self.after_index]
        ret_str = RoboticRoman.sanitize(joiner.join(quotes_list)).replace("_found", "").split(
            "--------------------------EOF--------------------------")[0].replace('. .', '. ').replace('..', '. ')
        if len(ret_str) >= 2000:
            ret_str = ret_str[:1998] + "..."
        return ret_str.replace(ABSOLUTE_DELIMITER, "")


class RoboticRoman():
    """
    Class encapsulating various bot functionality
    """

    def __init__(self, prefix):

        self.text_paths = [LATIN_TEXTS_PATH,
                           GREEK_TEXTS_PATH,
                           CHINESE_TEXTS_PATH,
                           GERMANIC_TEXTS_PATH]

        self.latin_lemmas = [w.strip() for w in open('latin_lemmas.txt').readlines()]
        self.parser = WiktionaryParser()
        self.parser.set_default_language('latin')
        # self.decliner = CollatinusDecliner()
        """
        self.reddit = praw.Reddit(client_id=os.environ['reddit_client_id'],
                                  client_secret=os.environ['reddit_secret'],
                                  user_agent='user agent')
        """

        self.latin_quotes_dict = dict()
        self.greek_quotes_dict = dict()
        self.chinese_quotes_dict = dict()
        self.germanic_quotes_dict = dict()

        self.quotes_dict_collection = [self.latin_quotes_dict,
                                       self.greek_quotes_dict,
                                       self.chinese_quotes_dict,
                                       self.germanic_quotes_dict]

        self.latin_authors = list(set([f.split('.')[0].replace('_', ' ') for f in os.listdir(LATIN_TEXTS_PATH)]))
        self.greek_authors = list(set([f.split('.')[0].replace('_', ' ') for f in os.listdir(GREEK_TEXTS_PATH)]))
        self.chinese_authors = list(set([f.split('.')[0].replace('_', ' ') for f in os.listdir(CHINESE_TEXTS_PATH)]))
        self.germanic_authors = list(set([f.split('.')[0].replace('_', ' ') for f in os.listdir(GERMANIC_TEXTS_PATH)]))

        self.authors_collection = [self.latin_authors, self.greek_authors, self.chinese_authors, self.germanic_authors]

        self.zipped = zip(self.authors_collection, self.quotes_dict_collection, self.text_paths)

        self.quote_tries = 0
        self.old_english_dict = {'jn': old_english_bible.john.john, 'lk': old_english_bible.luke.luke,
                                 'mk': old_english_bible.mark.mark, 'mt': old_english_bible.matthew.matthew}

        for author_collection, quotes_dict, directory in self.zipped:
            print(directory)
            for author in author_collection:
                quotes_dict[author] = [open('/'.join([directory, author, f]), encoding='utf8') for f in
                                       os.listdir(directory + "/" + author) if f.endswith('.txt')]

        self.commands = [(format_color("Get random quote by author ", "CSS"),
                          f"'{prefix}qt [-t (transliterate)] [-w[l][c] <regex search>] <author> | As <author> said:'" +
                          "\n\tNotes: adding 'c' to the -w option will make your search case-sensitive, and adding 'l' will search by word lemma rather than regex."),
                         (format_color("List available Latin authors ", "CSS"), f"'{prefix}latinauthors'"),
                         (format_color("Retrieve random Latin quote ", "CSS"), f"'{prefix}latinquote'"),
                         (format_color("Transliterate input ", "CSS"),
                          f"'{prefix}tr [-(language abbreviation)] <input>'" +
                          "\n\tNotes: Greek by default, heb -> Hebrew, cop -> Coptic, unc -> Uncial, oc -> Old Chinese, mc -> Middle Chinese, mand -> Mandarin, aram -> Aramaic, arab -> Arabic, syr -> Syriac, arm -> Armenian, geo -> Georgian, rus -> Russian, kor -> Hangul"),
                         (format_color("List Greek authors ", "CSS"), f"'{prefix}greekauthors'"),
                         (format_color("Retrieve random Greek quote ", "CSS"), f"'{prefix}greekquote'"),
                         (format_color("Retrieve random Chinese quote ", "CSS"), f"'{prefix}chinesequote'"),
                         (format_color("List Germanic authors ", "CSS"), f"'{prefix}germanicauthors'"),
                         (format_color("Retrieve random Germanic quote ", "CSS"), f"'{prefix}germanicquote'"),
                         (format_color("Retrieve random Latin quote ", "CSS"), f"'{prefix}latinquote'"),
                         (format_color("Start grammar game ", "CSS"), f"'{prefix}<language>_grammar'"),
                         (format_color("Start Latin grammar game ", "CSS"),
                          f"'{prefix}latin_grammar [-m] (with macrons)'"),
                         (format_color("Start word game ", "CSS"), f"'{prefix}wordgame [<language>]'"),
                         (format_color("Guess answer ", "CSS"), f"'{prefix}g <word>'"),
                         (format_color("End game ", "CSS"), f"'{prefix}giveup'"),
                         (format_color("Join game ", "CSS"), f"'{prefix}join <game owner>'"),
                         (format_color("Get available Bible versions ", "CSS"), f"'{prefix}bibleversions [<lang>]'"),
                         (format_color("Bible compare ", "CSS"),
                          f"'{prefix}biblecompare [<verse>] [$]<translation1> [$]<translation2>'" +
                          "\n\tNotes: add the prefix $ for transliteration."),
                         (format_color("Get Chinese character origin ", "CSS"), f"'{prefix}char_origin <character>'"),
                         (format_color("Get Chinese character origin from the Shuowen Jiezi", "CSS"),
                          f"'{prefix}getshuowen <character>'"),
                         (format_color("Start Shuowen game", "CSS"), f"'{prefix}shuowengame'"),
                         (format_color("Word definition (defaults to Latin) ", "CSS"),
                          f"'{prefix}<language>_def <word>'"),
                         (format_color("Word etymology (defaults to Latin) ", "CSS"),
                          f"'{prefix}<language>_ety <word>'"),
                         (format_color("Word entry (defaults to Latin) ", "CSS"), f"'{prefix}<language>_word <word>'"),
                         (format_color("Random entry (defaults to Latin) ", "CSS"),
                          f"'{prefix}randword [<language>]' | '{prefix}randomword [<language>]'"),
                         (format_color("Help ", "CSS"), f"'{prefix}helpme'")]

    def sort_files(self, file):
        try:
            return int(''.join([s.strip() for s in file if s.isdigit()]))
        except:
            return hash(file)

    def display_sort(x):
        x = x.replace('.txt', '')

        m = re.findall(r"[0-9]+", x)
        if m and len(m) != 0:
            return int(m[0])
        else:
            return int(''.join(str(ord(c)) for c in x.split('_')[0]))

    def show_author_works(self, author):
        """
        Display a list of works associated with an author

        :param author: the name of the author
        :return: "display_index" is a list of formatted strings to be displayed to the user, while "works" are the
        actual works themselves in the format that can be used to retrieve passages from them
        """
        author = author.lower()

        dic = self.map_person_to_dict(author)
        works = sorted(dic[author], key=lambda x: RoboticRoman.display_sort(x.name))
        work_names = [work.name.replace('.txt', '').replace('_', ' ').title().split('/')[-1] for work in works]
        display_index = '\n'.join([f"**{i + 1}.** {e}" for i, e in enumerate(work_names)])
        return display_index, works

    def fetch_def_by_other_parser(self, word_input, language):
        """
        An alternative parser for Wiktionary if the default one fails to retrieve the word definition

        :param word_input: the word to be searched
        :param language: the language in which to search for the word
        :return: the definition of the word in the target language
        """
        defs = []
        word = self.parser.fetch(word_input, language)
        for entry in word:
            try:
                defs.append(entry['definitions'][0]['text'])
            except:
                soup = my_wiktionary_parser.get_soup(word_input)
                try:
                    defs = my_wiktionary_parser.get_definitions(soup, language)
                except:
                    if language.lower == 'chinese' or language.lower == 'tradchinese':
                        soup = my_wiktionary_parser.get_soup(tradify(word_input))
                        defs = my_wiktionary_parser.get_definitions(soup, language)
                        return defs
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
        """
        Get the definition of a word from Wiktionary in the target language

        :param word_input: the word for which we wish to retrieve a list of definitions
        :param language: the language in which to search for the word
        :param include_examples: whether or not we want to include example usages of the word
        :return: the definitions of the word as listed in Wiktionary
        """
        defs = []
        try:
            soup = my_wiktionary_parser.get_soup(word_input)
            if "Wiktionary does not yet have an entry for " in str(soup):
                return ["Not found."]
            try:
                defs = my_wiktionary_parser.get_definitions(soup, language, include_examples)
            except:
                if language.lower() == 'chinese' or language.lower() == 'tradchinese':
                    soup = my_wiktionary_parser.get_soup(tradify(word_input))
                    defs = my_wiktionary_parser.get_definitions(soup, language, include_examples)
            if defs[0] == 'Not found':
                defs = self.fetch_def_by_other_parser(word_input, language)
            return defs
        except:
            defs = self.fetch_def_by_other_parser(word_input, language)
            if not defs:
                return "Not found"

    def word_is_in_wiktionary(self, word, language):
        """
        Check whether a word is indexed by Wiktionary in the given lannguage

        :param word: the word to look for
        :param language: the target language in which to search for the word
        :return: True if Wiktionary has an entry for the word in the given language, else return False
        """
        url = f"https://en.wiktionary.org/wiki/{word}"
        soup = my_wiktionary_parser.get_soup(word)
        return soup and "does not yet have an entry" not in soup

    def get_full_entry(self, word=None, language='latin', tries=0):
        """
        Retrieve the entire formatted entry of a word, including the definition, the etymology, and other information
        such as derivatives, if they are available on Wiktionary

        :param word: the word for which we wish to retrieve the entry
        :param language: the target language
        :param tries: the number of times we have tried to obtain the entry, currently stopping if this value exceeds 1
        :return: a formatted string containing word entry information retrieved from Wiktionary
        """
        if tries > 2:
            return "Error retrieving entry"
        if not word:
            word = self.get_random_word(language)
        if language.lower() == 'tradchinese':
            word = tradify(word)
            language = "chinese"
        soup = my_wiktionary_parser.get_soup(word)
        my_wiktionary_parser.destroy_translations(soup)
        my_wiktionary_parser.destroy_latin_correlatives(soup)
        for child in soup.children:
            if isinstance(child, Tag) and child.find_all('a', text="Latin correlatives"):
                for s in child.strings:
                    s = None
                child.decompose()
        try:
            definition = self.get_and_format_word_defs(word, language, include_examples=False)
        except:
            return self.get_full_entry(word, language, tries + 1)
        if definition == "1. Not found.":
            if word.istitle():
                return self.get_full_entry(word.lower(), language, tries + 1)
            if word.lower():
                return self.get_full_entry(word.title(), language, tries + 1)
        etymology = self.get_word_etymology(word, language)
        if language.lower() == 'chinese':
            word_header = self.get_word_header(word,
                                               language).strip() + "\n\n" + my_wiktionary_parser.get_historical_chinese_word(
                word)
        else:
            word_header = self.get_word_header(word, language).strip()
        if 'proto' in language.lower():
            derives = self.get_derivatives(word, language, misc=False)
            return_str = re.sub(r"(?<!\*)\*(?!\*)", "\\*",
                                f"{word_header}\n\n**Language:** {language.title()}\n\n**Definition:**\n{definition}\n\n**Etymology:**\n{etymology.strip()}\n\n{derives}")
        elif language.lower() == 'chinese':
            # print("WORD: " + word)
            gloss_section = ""
            if len(list(word)) > 1:
                gloss = my_wiktionary_parser.get_wiktionary_glosses(soup)
                if not gloss:
                    gloss = my_wiktionary_parser.get_wiktionary_glosses(my_wiktionary_parser.get_soup(tradify(word)))
                gloss_section = f"**Gloss:**\n{gloss}\n\n"
                print("In Muliple")
                glyph_origin = my_wiktionary_parser.get_glyph_origin_multiple(soup, list(word))
            else:
                glyph_origin = my_wiktionary_parser.get_glyph_origin(soup, word)
            if not glyph_origin:
                glyph_origin = "Not found."
            return_str = f"{word_header}\n\n**Language:** {language.title()}\n\n**Definition:**\n{definition}\n\n**Etymology:**\n{etymology.strip()}\n\n{gloss_section}**Glyph Origin:**\n{glyph_origin}"

        return_str = f"{word_header}\n\n**Language:** {language.title()}\n\n**Definition:**\n{definition}\n\n**Etymology:**\n{etymology.strip()}"
        # print(return_str)
        return_str = re.sub(r"\.mw-parser-output.*", "", return_str)
        double_derived_terms = re.compile(r"[\w\s]+\[edit\].*?\*\*", re.DOTALL)
        return_str = re.sub(double_derived_terms, "\n\n**", return_str)
        return_str = re.sub(r"Derived terms[^:]\n*", "", return_str)
        return_str = re.sub(r"Compounds[^:]\n*", "", return_str)
        return_str = re.sub(r"Synonyms[^:]\n*", "", return_str)
        return '\n' + return_str

    def get_derivatives(self, word, language='latin', misc=False):
        """
        Get the derivatives of a word from Wiktionary
        :param word: the input word
        :param language: the target language
        :param misc: currently not used
        :return:
        """
        soup = my_wiktionary_parser.get_soup(word)
        my_wiktionary_parser.destroy_translations(soup)
        my_wiktionary_parser.destroy_latin_correlatives(soup)
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
        """
        Get the etymology of a word from Wiktionary

        :param word: the input word
        :param language: the target language
        :param tries: the number of tries; we stop if this number exceeds QUOTE_RETRIEVAL_MAX_TRIES
        :return: the etymology of the word
        """
        if tries > QUOTE_RETRIEVAL_MAX_TRIES:
            return "No etymology found."
        if language.lower() == 'tradchinese':
            word = tradify(word)
            language = 'chinese'
        print("Word: " + str(word))
        try:
            language_section, soup = my_wiktionary_parser.get_language_header(word, language)
            etymology = my_wiktionary_parser.get_etymology(language_section, language, word).replace(u'\xa0', u' ')
            print(f"Etymology = {etymology}")
            if etymology == "Not found":
                if word.istitle():
                    print("Trying lower")
                    return self.get_word_etymology(word.lower(), language, tries + 1)
                if word.lower():
                    return self.get_word_etymology(word.title(), language, tries + 1)
            return etymology
        except:
            if language.lower() == 'chinese' or language.lower() == 'tradchinese':
                word = tradify(word)
                language_section, soup = my_wiktionary_parser.get_language_header(word, language)
                etymology = my_wiktionary_parser.get_etymology(language_section, language, word).replace(u'\xa0', u' ')
                return etymology
            traceback.print_exc()
            return "Not found."

    def get_random_word(self, language='latin', tries=0, category=None):
        """
        Retrieve a random word in the target language

        :param language: the language from which we wish to retrieve a random word
        :param tries: the number of tries; we stop if this number exceeds QUOTE_RETRIEVAL_MAX_TRIES
        :param category: the category of the word--useful for, say, retrieving a random Latin verb
        :return: a random word in the target language
        """
        if tries > QUOTE_RETRIEVAL_MAX_TRIES:
            return "Could not find lemma."
        if category:
            url = f"https://en.wiktionary.org/wiki/Special:RandomInCategory/{category}"
        elif language.lower().strip() == 'latin':
            word = word_picker.pick_word()
            return word
        elif language.lower().strip() == 'chinese':
            url = random.choice([f"https://en.wiktionary.org/wiki/Special:RandomInCategory/Middle_Chinese_lemmas",
                                 "https://en.wiktionary.org/wiki/Special:RandomInCategory/Chinese_chengyu",
                                 "https://en.wiktionary.org/wiki/Special:RandomInCategory/Mandarin_lemmas"])
            print(f"Chosen url: {url}")

        else:
            url = f"https://en.wiktionary.org/wiki/Special:RandomInCategory/{language.title()}_lemmas"
        response = requests.get(url)
        word_url = re.search(r'<link rel="canonical" href="(.*?)"/>', response.text).group(1)
        if "Reconstruction:" in word_url:
            word = word_url.split('/wiki/')[-1]
        else:
            word = urllib.parse.unquote(word_url.split('/')[-1].strip())
            if language.lower() == 'tradchinese':
                word = tradify(word)
                language = 'chinese'
        if "category:" in word.lower():
            return self.get_random_word(language, tries=tries + 1, category=word)
        etymology = self.get_word_etymology(word, language=language)
        print("Etymology in random: " + etymology)
        return urllib.parse.unquote(word).replace('_', ' ')

    def get_random_latin_lemma(self, tries=0):
        """
        Return a random Latin word in lemma form

        :param tries: the number of tries; we stop if this number exceeds QUOTE_RETRIEVAL_MAX_TRIES
        :return: a Latin word in lemma form, or an error message stating that we could not find a Latin lemma
        """
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

    def get_and_format_word_defs(self, word, language='latin', include_examples=False, tries=0):
        """
        Get the definitions of a word, and format them for output

        :param word: the word for which we wish to retrieve definitions
        :param language: the language in which we wish to search for the word
        :param include_examples: whether or not to include word usage examples
        :return: a formatted string displaying a numbered list of word definitions, each separated by a new line
        """
        if tries > QUOTE_RETRIEVAL_MAX_TRIES:
            return "1. Could not find definition."
        if language.lower() == 'tradchinese':
            word = tradify(word)
            language = 'chinese'
        word_defs = self.get_word_defs(word, language, include_examples)
        print(f"word_defs = {word_defs}")
        if word_defs[0] in ['Could not find definition.', 'Not found.']:
            if word.istitle():
                print("Trying lower")
                return self.get_and_format_word_defs(word.lower(), language, tries=tries + 1)
            if word.lower():
                return self.get_and_format_word_defs(word.title(), language, tries=tries + 1)
        if isinstance(word_defs, str):
            word_defs = [word_defs]
        return '\n'.join([f"{i + 1}. {e.strip()}" for i, e in enumerate(word_defs)]).replace(u'\xa0', u' ')

    def _fix_unclosed_quotes(text):
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

    def _passage_parallel_deliminator(text, delimiters=PARALLEL_DELIMITERS):
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

    def _passage_deliminator(text, delimiters=DELIMITERS):
        cur_sentence_len = 0
        prev_delimiter_pos = 0
        prev_delimiter = ""
        final_sentence = []

        unclosed_paren = False
        for i, c in enumerate(text):
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
        """
        Currently not used
        """
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
        return "Verse not found. Please check that you have a valid Bible version by checking here " \
               "https://www.biblegateway.com/versions, and here https://getbible.net/api. "

    def chunks(lst, n):
        """Yield successive n-sized chunks from l."""
        for i in range(0, len(lst), n):
            yield lst[i:i + n]

    def get_available_bible_versions(self):
        """
        Get a list of Bible versions in multiple languages from which we can retrieve passages for the sake of
        linguistic comparison

        :return: a formatted list of bible versions
        """
        return ', '.join(sorted([f"{key.title()}" for key in bible_versions.versions], key=str.lower))

    def get_available_bible_versions_lang(self, lang):
        """
        Get a list of Bible versions in a specific language

        :param lang: the language for which we wish to retrieve Bible versions
        :return: a list of Bible versions (such as KJV for English) in the specified language. The return type is
        a list, because the output can exceed 2000 characters, the maximum length of a Discord message, and thus
        may need to be broken down into smaller chunks.
        """
        versions = sorted(bible_versions.versions[lang.lower()], key=str.lower)
        return_string = f"{lang.title()}: {', '.join(versions)}"
        if len(return_string) >= 2000:
            chunks = RoboticRoman.chunks(versions, 10)
            return [lang.title() + ":"] + [f"{', '.join(chunk)}" for chunk in chunks]
        else:
            return [return_string]


    def get_old_english_verse(self, verse):
        """
        Retrieve a Bible passage from the Alfred the Great's Anglo-Saxon translation of the Vulgate

        :param verse: the Bible verses (e.g.  Romans 3:23) for which we wish to retrieve the Old English translation.
        Note that a range of verses, such as Matthew 6:9–13, is permitted.
        :return:
        """
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
        """
        Get a Bible verse using the getbible.net API

        :param verse: the Bible verses (e.g.  Romans 3:23) that we wish to retrieve. Note that a range of verses, such
        as Matthew 6:9–13, is permitted.
        :param version: the version of the Bible, such as the KJV or the Vulgate, from which we wish to retrieve the verse(s)
        :return: the passage from the given version of the Bible covered by the input verses
        """
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
        if "NULL" in response:
            raise Exception(f'No content found in ${url}')
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
        """
        Get a Bible verse from www.biblegateway.com.

        :param verse: the Bible verses (e.g.  Romans 3:23) that we wish to retrieve. Note that a range of verses, such
        as Matthew 6:9–13, is permitted.
        :param version: the version of the Bible, such as the KJV or the Vulgate, from which we wish to retrieve the verse(s)
        :return: the passage from the given version of the Bible covered by the input verses
        """
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
        """
        Get a verse from the Wycliffe Bible
        """
        url = f"https://studybible.info/Wycliffe/{verse}"
        body = requests.get(url).text
        soup = BeautifulSoup(body)
        passage = soup.find_all("div", {"class": "passage row Wycliffe"})[0]
        [s.extract() for s in soup('sup')]
        return re.sub(r"[\s]{2,}", "\n", passage.get_text().replace('Wycliffe', '').strip())

    def get_bible_verse(self, verse, version='kjv'):
        """
        Get a Bible verse from a given version. This implementation tries multiple sources until one is found which
        can successfully retrieve the given verse in the given version.

        :param verse: the Bible verses (e.g.  Romans 3:23) that we wish to retrieve. Note that a range of verses, such
        as Matthew 6:9–13, is permitted.
        :param version: the version of the Bible, such as the KJV or the Vulgate, from which we wish to retrieve the verse(s)
        :return: the passage from the given version of the Bible covered by the input verses
        """
        translit = False
        middle_chinese = False
        if version[0] == '$':
            version = ''.join(version[1:])
            translit = True
        if version[0] == '#':
            version = ''.join(version[1:])
            translit = True
            middle_chinese = True
        verse = verse.title()
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
        if version.strip.lower() == 'cc':
            try:
                return get_cc_passage(verse)
            except:
                traceback.print_exc()
                return "Not found"
        try:
            if version.strip().lower() in GETBIBLE_VERSIONS:
                try:
                    passage = self.get_bible_verse_by_api(verse, version)
                except:
                    passage = 'Not found'
                if passage == 'Not found':
                    try:
                        passage = self.get_bible_verse_from_gateway(verse, version)
                    except:
                        passage = "Not found"
            else:
                passage = self.get_bible_verse_from_gateway(verse, version)
            if translit:
                passage = self.transliterate_verse(version, passage, middle_chinese)
        except:
            traceback.print_exc()
            passage = "Not found"
        return passage.strip().replace("Read full chapter", "").replace("\n", " ")

    def get_random_verse_by_testament(self, testament):
        """
        Get a random verse from either the Old Testament or the New Testament
        :param testament: can be either "ot" or "nt"
        :return: a random verse
        """
        with open(f"bible_verses_{testament}.txt") as file:
            verses = file.read().split('|')
            return random.choice(verses).title()

    def get_gothic_verses_set(self):
        """
        Get a hash set of verses available in Ulfilas' Gothic translation of the Bible.
        """
        with open('off_topic_texts/ulfilas/gothic_bible.txt', encoding='utf8') as file:
            text = file.read()
            return set([v.lower() for v in re.findall(r"\w+\s[0-9]+:[0-9]+", text)])

    def get_old_english_verses_set(self):
        """
        Get a hash set of verses available in Alfred's Old English translation of the Bible.
        """
        final = []
        for book in self.old_english_dict.keys():
            chapters = self.old_english_dict[book].keys()
            for chapter in chapters:
                verses = self.old_english_dict[book][chapter].keys()
                for verse in verses:
                    final.append(f"{book} {chapter}:{verse}")
        return set(final)

    def get_random_verse(self):
        """
        Get a random Bible verse.
        """
        with open(f"bible_verses.txt") as file:
            verses = file.read().split('|')
            return random.choice(verses).title()

    def bible_compare_random_verses(self, versions: list):
        """
        Given a list of Bible versions, pick a random verse and return the translations of that verse offered
        by each version.
        """
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

    def transliterate_verse(self, version, text, middle_chinese):
        """
        Given a Bible version and text, if the Bible version is in a list of language-specific Bible versions (such as
        Russian Bibles or Chinese Bibles) for which transliteration is supported, transliterate the given text from the
        source script to Latin characters

        :param version: currently supports Coptic, Aramaic, Arabic, Greek, Russian, Armenian, Georgian, Korean, and
        Chinese. We have an option of transliterating into Middle Chinese instead of Mandarinn if the version is Chinese.
        :param text: the text we wish to transliterate.
        :param middle_chinese: boolean flag to transliterate into Middle Chinese instead of Mandarin if the version is
        a Chinese Bible translation
        :return: the transliterated text, or the original text if it cannot be transliterated
        """
        version = version.lower()

        if version in COPTIC:
            text = transliteration.coptic.transliterate(text).lower()
        if version in ARAMAIC:
            r = romanize3.__dict__['syc']
            text = r.convert(text)
        if version in HEBREW:
            text = transliteration.hebrew.transliterate(text).lower()
        if version in ARABIC:
            text = arabtex.transliterate(text)
        if version in GREEK:
            text = transliteration.greek.transliterate(text)
        if version in RUSSIAN:
            text = translit(text, 'ru', reversed=True)
        if version in BULGARIAN:
            text = translit(text, 'bg', reversed=True)
        if version in SERBIAN:
            text = translit(text, 'sr', reversed=True)
        if version in UKRAINIAN:
            text = translit(text, 'uk', reversed=True)
        if version in ARMENIAN:
            text = translit(text, 'hy', reversed=True).replace('ւ', 'v')
        if version in GEORGIAN:
            text = translit(text, 'ka', reversed=True).replace('ჲ', 'y')
        if version == "uncial":
            text = transliteration.latin_antique(text)
        if version in KOREAN:
            text = transliteration.korean.transliterate(text)
        if version in CHINESE:
            if middle_chinese:
                text = transliteration.middle_chinese.transliterate(text).replace("  ", " ")
            else:
                text = transliteration.mandarin.transliterate(text).replace("  ", " ")
        return text.replace("Read full chapter", "")

    def bible_compare(self, verse, versions: list):
        """
        Given a verse and a list of Bible versions, compare different renderings of the verse in the different versions

        :param verse: the Bible verse (e.g. "2 Corinthians 6:10")
        :param versions: a list of Bible versions (e.g. "KJV," "CCBT, etc.)
        :return: a formatted string consisting of a new-line separated list of renderings of the same Bible verse in the
        given versions
        """
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

    def bible_compare_random(self, versions: list):
        if 'gothic' in [version.strip().lower() for version in versions]:
            verse = self.get_gothic_verse()
        else:
            verse = self.get_random_verse()
        return self.bible_compare(verse, versions)

    def _replace_placeholders(text):
        for key in REVERSE_DELIMITERS_MAP:
            text = text.replace(key, REVERSE_DELIMITERS_MAP[key])
        return text

    def _process_basic(text):
        return ['. '.join(s) + '.' for s in list(RoboticRoman.chunks(text.split('.'), 3))]

    def _process_mixed(text):
        if ABSOLUTE_DELIMITER in text:
            return RoboticRoman._process_absolute(text=text)
        return RoboticRoman._process_text(text)

    def _process_absolute(text):
        splitted = text.split(ABSOLUTE_DELIMITER)
        return [w.replace(ABSOLUTE_DELIMITER, "") for w in splitted]

    def _process_text(text):
        text = RoboticRoman._replace_abbreviation_period(text.replace('...', '^'))
        text = RoboticRoman._passage_deliminator(text)
        text = re.sub(r"[\n]{2,}|(\n+\s+){2,}|(\s+\n+){2,}", "\n\n", text)
        first_pass = [s for s in re.split(DELIMITERS_REGEX, text)]
        return [re.sub(REGEX_SUB, '', t) + (first_pass[i + 1] if first_pass[i + 1] != '|' else '') for i, t in
                enumerate(first_pass) if 'LIBRARY' not in t.upper()
                and t.strip().replace('\n', '') != '' and MIN_QUOTES_LENGTH < len(t) < MAX_QUOTES_LENGTH and
                i < len(first_pass) - 1]

    def _process_parallel(text):
        text = RoboticRoman._replace_abbreviation_period(text.replace('...', '^'))
        text = RoboticRoman._passage_parallel_deliminator(text, delimiters=PARALLEL_DELIMITERS)
        text_list = text.split('\n')
        # text_list = [t.replace('@', '\n') for t in text_list]
        return text_list

    def splitkeepsep(self, s, sep):
        return reduce(lambda acc, elem: acc[:-1] + [acc[-1] + elem] if re.match(elem, sep) else acc + [elem],
                      re.split("(%s)" % re.escape(sep), s), [])

    def _process_holy_text(scripture):
        first_pass = re.sub(r"CAPUT\s*([0-9]+)", r"CAPUT \1:", scripture)
        second_pass = [s for s in re.split(r"(" + BIBLE_DELIMITERS + ")", first_pass)]
        # print(second_pass)
        third_pass = [re.sub(r"[0-9]+$", "", s.replace('\n', '').strip()) + " " + second_pass[i + 1] if i + 1 < len(
            second_pass) and len(s.strip()) > 4 else None for i, s in enumerate(second_pass)]
        # print(third_pass)
        return [re.sub(r"([0-9])+\s\.", "\1 ", s) for s in third_pass if s]
        # return [s for s in re.split(BIBLE_DELIMITERS, RoboticRoman._replace_abbreviation_period(first_pass))
        #        if 'LATIN' not in s.upper() and 'LIBRARY' not in s.upper() and s.strip().replace('\n', '') != ''
        #        and MIN_QUOTES_LENGTH < len(s) < MAX_QUOTES_LENGTH]

    def _replace_abbreviation_period(text):
        for abbreviations in ABBREVIATIONS:
            text = text.replace(" " + abbreviations + '.', " " + abbreviations + '%')
        return text

    def load_all_models(self):
        for author, quotes_dict, text_path in self.zipped:
            self.load_quotes(quotes_dict, text_path, author)
        print("Finished loading models")

    def load_quotes(self, quotes_dict, path, author):
        quotes_dict[author] = []
        author_path = f"{path}/{author}/"
        for file in os.listdir(author_path):
            if file.endswith('.txt'):
                quotes_dict[author].append(open(f"{author_path}/{file}", encoding='utf8'))

    def format_name(self, author):
        return author.title().replace('Of ', 'of ').replace('The ', 'the ').replace(' De ', ' de ')

    def pick_quote_generic(self, quote_dict):
        author = random.choice(list(quote_dict.keys()))
        return f"{self.random_quote(author)[1]}\n\t―{self.format_name(author)}"

    def pick_random_literature_quote(self):
        author = random.choice(list(self.literature_quotes_dict.keys()))
        return f"{self.random_quote(author)[1]}\n\t―{self.format_name(author)}"

    def pick_random_philosopher_quote(self):
        author = random.choice(list(self.philosophers_quotes_dict.keys()))
        return f"{self.random_quote(author)[1]}\n\t―{self.format_name(author)}"

    def pick_random_germanic_quote(self):
        author = random.choice(list(self.germanic_quotes_dict.keys()))
        return f"{self.random_quote(author)[1]}\n\t―{self.format_name(author)}"

    def pick_random_latin_quote(self):
        author = random.choice(list(self.latin_quotes_dict.keys()))
        return f"{self.random_quote(author)[1]}\n\t―{self.format_name(author)}"

    def pick_random_chinese_quote(self):
        author = random.choice(list(self.chinese_quotes_dict.keys()))
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
            return i, quotes, self.find_multi_regex(regex,
                                                    re.sub(r"[^\w0-9\s\n]", "", proces_func(quote), case_sensitive))

    def unpack(self, *lst):
        return lst

    def remove_accents(self, input_str):
        if isinstance(input_str, bytes) or isinstance(input_str, bytearray):
            input_str = input_str.decode('utf8')
        nfkd_form = unicodedata.normalize('NFKD', input_str)
        return u"".join([c for c in nfkd_form if not unicodedata.combining(c)])

    def pick_quote_modular(self, modules, word=None, lemmatize=False, case_sensitive=False, tries=0):
        # print(', '.join([f.name for f in files]))
        print("Case_sensitive: " + str(case_sensitive))
        if tries > 2:
            return -1, "Not found.", []
        if word:
            word = self.remove_accents(word).lower() if not case_sensitive else word
            regex_list = []
            if lemmatize:
                pass
                # try:
                # words = self.flatten([[f"{word} ", f" {word} ", f" {word}."] for word in self.decliner.decline(word, flatten=True)])
                # inflected = self.decliner.decline(word, flatten=True)
                # for form in inflected:
                # regex_list.append(f"\\b{form}\\b")
                # except:
                # traceback.print_exc()
                # return -1, "Unknown lemma.", []
            else:
                # words = ['|'.join([f"(^{word}\\b+?)", f"(\\b{word}\\b+?)", f"(\\b{word}\\.)"])]
                # words = [f"{word} ", f" {word} ", f" {word}."]
                regex_list.append(f"\\b{word}\\b")
                # words = [r"(\s" + word + r"\s|^" + word + r"|\s" + word + r"\.)"]
            print(regex_list)
            search_quotes = []
            quotes_list = []
            all_quotes = []
            for module in modules:
                # print([re.sub(r"[^a-z0-9\s\n]", "", p.lower()) for p in process_func(f.read())])
                quotes = []
                print(f"Module file: {module.__file__}")
                if 'footnotes' not in module.__file__:
                    quotes = module.quotes
                else:
                    quotes = []
                    for chapter in module.footnotes:
                        quotes += [fn.lstrip() + '\n\n' for fn in module.footnotes[chapter]]
                for p in quotes:
                    search_target = self.find_multi_regex(regex_list,
                                                          re.sub(r"[^\w0-9\s\n]", "", self.remove_accents(p)),
                                                          case_sensitive)
                    if search_target:
                        search_quotes.append(p)
                        quotes_list.append(p + "_found")
                    else:
                        quotes_list.append(p)
                quotes_list.append("--------------------------EOF--------------------------")
            if len(search_quotes) == 0:
                print("Search_quotes is 0")
                #j = JVReplacer()
                index, quote, quotes_list = self.pick_quote_modular(modules, word, lemmatize, case_sensitive,
                                                                    tries + 1)
                if not search_quotes or len(search_quotes) == 0:
                    return -1, "Not found.", []
            else:
                return_values = []
                for i, quote in enumerate(quotes_list):
                    if quote.endswith("_found"):
                        return_values.append((i, quote.replace("_found", "")))
                ret = random.choice(return_values)
                # print("Return: " + str(ret))
                return ret[0], ret[1], quotes_list
        else:
            vol_index = random.randint(0, len(modules) - 1)
            volume = modules[vol_index]
            if 'footnotes' in volume.__file__:
                quotes = []
                for chapter in volume:
                    quotes += volume[chapter]
                quotes_list = quotes
            else:
                quotes_list = volume.quotes
            quote_index = random.randint(0, len(quotes_list) - 1)
            quote = quotes_list[quote_index]
            return quote_index, quote, quotes_list
        return index, quote, quotes_list

    def pick_quote(self, files, process_func, word=None, lemmatize=False, case_sensitive=False, tries=0, chinese=False):
        # print(', '.join([f.name for f in files]))
        print("Case_sensitive: " + str(case_sensitive))
        if tries > 2:
            return -1, "Not found.", []
        if word:
            word = self.remove_accents(word).lower() if not case_sensitive else word
            regex_list = []
            if lemmatize:
                try:
                    # words = self.flatten([[f"{word} ", f" {word} ", f" {word}."] for word in self.decliner.decline(word, flatten=True)])
                    inflected = self.decliner.decline(word, flatten=True)
                    for form in inflected:
                        regex_list.append(f"\\b{form}\\b")
                except:
                    traceback.print_exc()
                    return -1, "Unknown lemma.", []
            else:
                # words = ['|'.join([f"(^{word}\\b+?)", f"(\\b{word}\\b+?)", f"(\\b{word}\\.)"])]
                # words = [f"{word} ", f" {word} ", f" {word}."]
                if chinese:
                    regex_list.append(f"{word}")
                else:
                    regex_list.append(f"\\b{word}\\b")
                # words = [r"(\s" + word + r"\s|^" + word + r"|\s" + word + r"\.)"]
            print(regex_list)
            search_quotes = []
            quotes_list = []
            all_quotes = []
            read_files = []
            j_index = 0
            for i, f in enumerate(files):
                print(str(i) + " " + f.name)
                # print([re.sub(r"[^a-z0-9\s\n]", "", p.lower()) for p in process_func(f.read())])
                read_file = process_func(f.read())
                read_files.append(read_file)
                for j, p in enumerate(read_file):
                    j_index = j
                    all_quotes.append(p)
                    search_target = self.find_multi_regex(regex_list,
                                                          re.sub(r"[^\w,0-9\s\n]", "", self.remove_accents(p)),
                                                          case_sensitive)
                    if search_target:
                        search_quotes.append(p)
                        quotes_list.append((j, p + "_found", i))
                    else:
                        quotes_list.append((j, p, i))
                quotes_list.append((j_index + 1, "--------------------------EOF--------------------------", i))
                f.seek(0)
            if len(search_quotes) == 0:
                print("Search_quotes is 0")
                #j = JVReplacer()
                index, quote, quotes_list = self.pick_quote(files, process_func, word, lemmatize,
                                                            case_sensitive, tries + 1)
                if not quote:
                    return -1, "Not found.", []
            else:
                return_values = []
                for i, (j, quote, f_index) in enumerate(quotes_list):
                    if quote.endswith("_found"):
                        return_values.append((j, quote.replace("_found", ""), f_index))
                ret = random.choice(return_values)
                return ret[0], ret[1], read_files[ret[2]]
        else:
            f = random.choice(files)
            f.seek(0)
            quotes_list = process_func(f.read())
            index = i = random.choice(range(len(quotes_list)))
            quote = quotes_list[index]
            f.seek(0)
        if process_func.__name__ == "_process_absolute":
            quote.replace(ABSOLUTE_DELIMITER, "")
            quotes_list = [q.replace(ABSOLUTE_DELIMITER, "") for q in quotes_list]

        return index, quote, quotes_list

    def get_passage_list_for_file(self, file, process_func):
        print(file)
        print(process_func)
        passage_list = process_func(file.read())
        if process_func.__name__ == "_process_absolute":
            passage_list = [w.replace(ABSOLUTE_DELIMITER, "") for w in passage_list]
        return passage_list

    def get_text_list_for_person(self, person):
        if person in self.greek_quotes_dict:
            files = self.greek_quotes_dict[person]
        elif "the " + person in self.greek_quotes_dict:
            files = self.greek_quotes_dict["the " + person]
        else:
            if person not in self.latin_quotes_dict:
                person = "the " + person
            files = self.latin_quotes_dict[person]
        file = random.choice(files).read()
        if person == 'the bible':
            return re.split(BIBLE_DELIMITERS, file)
        return file.split('.')

    def get_quote_list(self, person, word, lemmatize=False, case_sensitive=False):
        if person in self.greek_quotes_dict:
            files = self.greek_quotes_dict[person]
            try:
                i, quote = self.pick_quote(files, RoboticRoman._process_text, word, lemmatize, case_sensitive)
            except Exception as error:
                if self.quote_tries < QUOTE_RETRIEVAL_MAX_TRIES:
                    self.quote_tries += 1
                    i, quote = self.pick_quote(files, RoboticRoman._process_text, word, lemmatize, case_sensitive)
                    return quote
                else:
                    self.quote_tries = 0
                    raise error
        elif "the " + person in self.greek_quotes_dict:
            files = self.greek_quotes_dict["the " + person]
            try:
                i, quote = self.pick_quote(files, RoboticRoman._process_text, word, lemmatize, case_sensitive)
            except Exception as error:
                if self.quote_tries < QUOTE_RETRIEVAL_MAX_TRIES:
                    self.quote_tries += 1
                    i, quote = self.pick_quote(files, RoboticRoman._process_text, word, lemmatize, case_sensitive)
                    return i, quote
                else:
                    self.quote_tries = 0
                    raise error
        elif person in self.off_topic_authors:
            files = self.off_topic_quotes_dict[person]
            if person.lower() == "joyce":
                quote = self.pick_quote(files, RoboticRoman._process_basic, word, lemmatize, case_sensitive)
            elif person.lower() == "bush" or person.lower() == "yogi berra":
                i, quote = self.pick_quote(files, RoboticRoman._process_absolute, word, lemmatize, case_sensitive)
                print(quote)
            else:
                i, quote = self.pick_quote(files, RoboticRoman._process_text, word, lemmatize, case_sensitive)
        elif 'the ' + person in self.off_topic_authors:
            files = self.off_topic_quotes_dict['the ' + person]
            i, quote = self.pick_quote(files, RoboticRoman._process_text, word, lemmatize, case_sensitive)
        elif 'parallel_' in person:
            files = self.parallel_quotes_dict[person.replace('parallel_', '')]
            i, quote = self.pick_quote(files, RoboticRoman._process_parallel, word, lemmatize, case_sensitive)
            print("Parallel quote: " + quote)
        else:
            if not person in self.latin_quotes_dict:
                person = "the " + person
            files = self.latin_quotes_dict[person]
            if person == 'the bible':
                i, quote = self.pick_quote(files, RoboticRoman._process_holy_text, word, lemmatize, case_sensitive)
            elif person == 'phrases':
                res = [(i, e) for i, e in
                       enumerate(open({LATIN_TEXTS_PATH} // "phrases" // "phrases.txt").read().split("円"))]
                print(res)
                index = random.randint(0, len(res))
                i = index
                quote = res[i]
                return quote
            else:
                i, quote = self.pick_quote(files, RoboticRoman._process_text, word, lemmatize, case_sensitive)
        return re.sub(r"^[\s]*[\n]+[\s]*", " ",
                      RoboticRoman.fix_crushed_punctuation(RoboticRoman._replace_placeholders(quote)))

    def map_person_to_dict(self, person):
        for dic in self.quotes_dict_collection:
            if person.lower() in dic:
                return dic
        return None

    def random_quote(self, person, word=None, lemmatize=False, case_sensitive=False):
        quotes_dict = self.map_person_to_dict(person.lower())
        if not quotes_dict:
            person = "the " + person.lower().strip()
            quotes_dict = self.map_person_to_dict(person)
            if not quotes_dict:
                return "Given author not available yet."
        else:
            person = person.lower().strip()

        files = quotes_dict[person.lower()]

        person = person.lower().strip()

        if person == 'bush':
            i, quote, quotes_list = self.pick_quote(files, RoboticRoman._process_absolute, word, lemmatize,
                                                    case_sensitive)
        elif person == 'yogi berra':
            i, quote, quotes_list = self.pick_quote(files, RoboticRoman._process_absolute, word, lemmatize,
                                                    case_sensitive)
        elif person == 'the bible':
            i, quote, quotes_list = self.pick_quote(files, RoboticRoman._process_holy_text, word, lemmatize,
                                                    case_sensitive)
        elif person == 'phrases':
            i, quote, quotes_list = self.pick_quote(files, RoboticRoman._process_absolute, word, lemmatize,
                                                    case_sensitive)
        elif person == 'mommsen':
            files = [f for f in files if 'content' not in f.name]
            index_files = [f for f in files if 'content' in f.name]
            i, quote, quotes_list = self.pick_quote(files, RoboticRoman._process_text, word, lemmatize, case_sensitive)
        elif person == 'gibbon':
            i, quote, quotes_list = self.pick_quote(files, RoboticRoman._process_mixed, word, lemmatize, case_sensitive)
        elif person in self.chinese_authors:
            i, quote, quotes_list = self.pick_quote(files, RoboticRoman._process_text, word, lemmatize, case_sensitive,
                                                    chinese=True)
        else:
            i, quote, quotes_list = self.pick_quote(files, RoboticRoman._process_text, word, lemmatize, case_sensitive)
        return i, re.sub(r"^[\s]*[\n]+[\s]*", " ", RoboticRoman.sanitize(quote)), quotes_list

    def sanitize(quote):
        return RoboticRoman.fix_crushed_punctuation(RoboticRoman._replace_placeholders(quote))

    def fix_crushed_punctuation(text):
        text = re.sub(r"(\w)\.([^\s])", r"\1. \2", text)
        text = re.sub(r"(\w);([^\s])", r"\1; \2", text)
        text = re.sub(r"(\w)\?([^\s])", r"\1? \2", text)
        text = re.sub(r"(\w)!([^\s])", r"\1! \2", text)
        text = re.sub(r"(\w):([^\s])", r"\1: \2", text)
        text = text.replace("。.", "。").replace("？.", "？").replace("！.", "！")
        return text

    def pick_greek_quote(self):
        author = random.choice(list(self.greek_quotes_dict.keys()))
        return f"{self.random_quote(author)[1]}\n\t―{self.format_name(author)}"


    def get_shuowen(self, c):
        explanation = my_wiktionary_parser.get_shuowen(c)
        if not explanation:
            explanation = "Could not find glyph origin in Shuowen"
        return explanation

    def shuowen_game(self):
        char_id = str(random.randint(1, 9833))
        char_url = "http://www.shuowenjiezi.com/result4.php?id=" + char_id
        print(char_url)
        soup = BeautifulSoup(requests.get(char_url).content)
        # print(soup)
        explanation = soup.find('div', attrs={'class': 'chinese'})
        for div in explanation.find_all("a", {'class': 'isAnyDuanzhu'}):
            div.decompose()
        character = chr(int(
            '0x' + soup.find('span', attrs={'id': 'radical0'})['onclick'].split(',')[0].split('(')[1].replace('\'', ''),
            16))
        pinyin = soup.find('span', attrs={'id': 'pinyin0'}).getText()
        return character, explanation.getText(), pinyin

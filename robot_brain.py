from functools import reduce
import json
import os
import random
import re
import string
import traceback
import unicodedata
import urllib

from bs4 import BeautifulSoup, Tag
from lang_trans.arabic import arabtex
from mafan import tradify
import requests
import romanize3
from transliterate import translit
from wiktionaryparser import WiktionaryParser

from bible_compare import bible_versions, getbible_books_to_numbers
from bible_compare.bible_versions import lang_to_versions
from bible_compare.classical_chinese_bible import get_cc_verses
from bible_compare.gateway_abbreviations import abbreviations
from bible_compare.meiji_japanese_bible import get_meiji_japanese_verses
import bible_compare.old_english_bible.john
import bible_compare.old_english_bible.luke
import bible_compare.old_english_bible.mark
import bible_compare.old_english_bible.matthew
from constants import GET_BIBLE_BASE_URL, GET_BIBLE_LEGACY_BASE_URL
from latin_word_picker import word_picker
import my_wiktionary_parser
import transliteration.coptic
import transliteration.greek
import transliteration.hebrew
import transliteration.korean
import transliteration.mandarin
import transliteration.middle_chinese
import transliteration.old_chinese
import transliteration.japanese

# Relative paths to files containing source texts
LATIN_TEXTS_PATH = "latin_texts"
GREEK_TEXTS_PATH = "greek_texts"
CHINESE_TEXTS_PATH = "chinese_texts"
GERMANIC_TEXTS_PATH = "germanic_texts"

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

# Reverse delimiter map to map the temporary sentence pseudo-delimiters back to their original characters in the
# final output
REVERSE_DELIMITERS_MAP = {'%': '.', '#': '?', '$': '!', '^': '...', '¡': '。', '±': '！', '∓': '？', '‰': '\n'}

# Regex expression of characters that need to be exterminated with extreme prejudice
REGEX_SUB = re.compile(r"\[|]|\(\)")

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

EOF = "--------------------------EOF--------------------------"

CHINESE_WORD_CHOICES = ["https://en.wiktionary.org/wiki/Special:RandomInCategory/Middle_Chinese_lemmas",
                        "https://en.wiktionary.org/wiki/Special:RandomInCategory/Mandarin_lemmas"]

COPTIC = ['bohairic', 'sahidic', 'coptic']
ARAMAIC = ['peshitta']
LATIN = ["vulgate", "newvulgates"]
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
CHINESE = ['ccb', 'ccbt', 'erv-zh', 'cns', 'cnt', 'cus', 'cut', 'cc']
JAPANESE = ['jlb', 'meiji']

# Does nothing at the moment. May be useful when Discord has better color support
def format_color(text, color_type="yaml"):
    # Nothing for now
    return text


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
        ret_str = RobotBrain.sanitize(joiner.join(quotes_list)).replace("_found", "").split(EOF)[0] \
            .replace('. .', '. ').replace('..', '. ')
        if len(ret_str) >= 2000:
            ret_str = ret_str[:1998] + "..."
        return ret_str.replace(ABSOLUTE_DELIMITER, "")


class RobotBrain:
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
        self.old_english_dict = {'jn': bible_compare.old_english_bible.john.john,
                                 'lk': bible_compare.old_english_bible.luke.luke,
                                 'mk': bible_compare.old_english_bible.mark.mark,
                                 'mt': bible_compare.old_english_bible.matthew.matthew}

        for author_collection, quotes_dict, directory in self.zipped:
            for author in author_collection:
                quotes_dict[author] = [open('/'.join([directory, author, f]), encoding='utf8') for f in
                                       os.listdir(directory + "/" + author) if f.endswith('.txt')]

        self.commands = [
            (format_color("Get random quote by author ", "CSS"), f"`{prefix}qt [-t] [-w[c] <regex>] <author>`" +
             "\n\tOptions:"
             "\n\t\t**-t**: transliterate the quote."
             "\n\t\t**-w**: search for a quote containing an expression matching the supplied regex. Add 'c' to make "
             "your search case-sensitive"
             "\n\tExample: `qt -w Marc.* Livy`"),
            (format_color("Transliterate input ", "CSS"), f"`{prefix}tr [-<language>] <input>`" +
             "\n\tNotes: Current transliteration options are -gre (Greek), -heb (Hebrew), -cop (Coptic), -oc (Old "
             "Chinese), -mc (Middle Chinese), -mand (Mandarin), -aram (Aramaic), -arab (Arabic), -syr (Syriac), "
             "-arm (Armenian), -geo (Georgian), -rus (Russian), -kor (Korean) -jap (Japanese)"
             "\n\tExample: `tr -rus \"я не умею читать кириллицу\"`"),
            (format_color("List Latin authors ", "CSS"), f"`{prefix}latinauthors`"),
            (format_color("List Greek authors ", "CSS"), f"`{prefix}greekauthors`"),
            (format_color("List Chinese authors ", "CSS"), f"`{prefix}chineseauthors`"),
            (format_color("List Germanic authors ", "CSS"), f"`{prefix}chineseauthors`"),
            (format_color("Retrieve a random Latin quote ", "CSS"), f"`{prefix}latinquote`"),
            (format_color("Retrieve a random Greek quote ", "CSS"), f"`{prefix}greekquote [-t]`"
                                                                    f"\n\tOptions:"
                                                                    f"\n\t\t**-t**: transliterate the quote."),
            (format_color("Retrieve a random Chinese quote ", "CSS"), f"`{prefix}chinesequote`"),
            (format_color("Retrieve a random Germanic quote ", "CSS"), f"`{prefix}germanicquote`"),
            (format_color("Start a grammar game ", "CSS"), f"`{prefix}grammargame [-m] <language>`"
                                                           f"\n\tOptions:"
                                                           f"\n\t\t**-m**: require correct macrons."),
            (format_color("Start a word game (where you'll guess the word based on its definition)", "CSS"),
             f"`{prefix}wordgame <language>`"),
            (format_color("Start a text game (where you'll guess the author based on a piece of text) ", "CSS"),
             f"`{prefix}textgame <language>`"),
            (format_color("Guess answer ", "CSS"), f"`{prefix}g <word>`"),
            (format_color("End game ", "CSS"), f"`{prefix}giveup`"),
            (format_color("Join game ", "CSS"), f"`{prefix}join <game owner>`"),
            (format_color("Get available Bible versions", "CSS"), f"`{prefix}bibleversions [language]`"
                                                                  f"\n\tNotes: Type `bibleversions` to get a list of "
                                                                  f"languages for which Bible translations are "
                                                                  f"available, and `bibleversions [language]` to get "
                                                                  f"a list of Bible translations for a particular "
                                                                  f"language"),
            (format_color("Compare bible versions ", "CSS"),
             f"`{prefix}comparebible <verses> [$]<translation1> [$]<translation2> ...`" +
             "\n\tNotes: The translation options can be a specific Bible translation, such as the KJV, or a language, "
             "such as Japanese, which will use a default translation. These can be mixed freely. Note also that some "
             "translations contain only the Old or New Testament, while others may be missing entire books--Aelfric's "
             "Old English translation, for example, has only the Gospels."
             "\n\tExample: `comparebible Genesis 1:1-3 $lxx vulgate hebrew`"),
            (
                format_color("Get Chinese character origin from Wiktionary ", "CSS"),
                f"`{prefix}char_origin <character>`"),
            (format_color("Get Chinese character origin from the [Shuowen Jiezi]("
                          "https://en.wikipedia.org/wiki/Shuowen_Jiezi)", "CSS"),
             f"`{prefix}getshuowen <character>`"),
            (format_color("Start Shuowen game", "CSS"), f"`{prefix}shuowengame`"),
            (format_color("Word definition", "CSS"), f"`{prefix}getdef <language> <word>`"),
            (format_color("Word etymology", "CSS"), f"`{prefix}getety <language> <word>`"),
            (format_color("Word entry ", "CSS"), f"`{prefix}getentry <language> <word>`"),
            (format_color("Random entry (defaults to Latin) ", "CSS"),
             f"`{prefix}randword [language]' | '{prefix}randomword [language]`"),
            (format_color("Help ", "CSS"), f"`{prefix}helpme`")]


    @staticmethod
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
        works = sorted(dic[author], key=lambda x: RobotBrain.display_sort(x.name))
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


    def strip_html_tags(self, text):
        """
        Remove HTML tags from the given text.

        Args:
            self (str): Text that may contain HTML tags.

        Returns:
            str: Cleaned text without HTML tags.
        """
        return re.sub(r'<[^>]+>', '', text)


    def get_word_definitions(self, word, language='la', include_examples=True):
        """
        Get the definition of a word from Wiktionary in the target language

        :param word: the word for which we wish to retrieve a list of definitions
        :param language: the language in which to search for the word
        :param include_examples: whether or not we want to include example usages of the word
        :return: the definitions of the word as listed in Wiktionary
        """
        url = f"https://en.wiktionary.org/api/rest_v1/page/definition/{word}"

        try:
            response = requests.get(url)
            response.raise_for_status()  # Raises HTTPError for bad responses

            data = response.json()

            # Check if definitions for the specified language exist
            if language in data:
                definitions = []
                for entry in data[language]:
                    for sense in entry['definitions']:
                        print(f'sense: {sense}')
                        definitions.append(self.strip_html_tags(sense['definition']))
                print(definitions)
                return definitions
            else:
                return f"No definitions found for the language '{language}' for the word '{word}'."

        except requests.exceptions.RequestException as e:
            return f"Error fetching data: {e}"


    def get_full_entry(self, word=None, language='latin', tries=0):
        """
        Retrieve the entire formatted entry of a word, including the definition, the etymology, and other information
        such as derivatives, if they are available on Wiktionary

        :param word: the word for which we wish to retrieve the entry
        :param language: the target language
        :param tries: the number of times we have tried to obtain the entry, currently stopping if this value exceeds 1
        :return: a formatted string containing word entry information retrieved from Wiktionary
        """
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
                                f"{word_header}\n\n**Language:** {language.title()}\n\n**Definition:**\n{definition}"
                                f"\n\n**Etymology:**\n{etymology.strip()}\n\n{derives}")
        elif language.lower() == 'chinese':
            # print("WORD: " + word)
            gloss_section = ""
            if len(list(word)) > 1:
                gloss = my_wiktionary_parser.get_wiktionary_glosses(soup)
                if not gloss:
                    gloss = my_wiktionary_parser.get_wiktionary_glosses(my_wiktionary_parser.get_soup(tradify(word)))
                gloss_section = f"**Gloss:**\n{gloss}\n\n"
                print("In multiple")
                glyph_origin = my_wiktionary_parser.get_glyph_origin_multiple(list(word))
            else:
                glyph_origin = my_wiktionary_parser.get_glyph_origin(soup, word)
            if not glyph_origin:
                glyph_origin = "Not found."
            return f"{word_header}\n\n**Language:** {language.title()}\n\n**Definition:**\n{definition}\n\n" \
                   f"**Etymology:**\n{etymology.strip()}\n\n{gloss_section}**Glyph Origin:**\n{glyph_origin}"

        return_str = f"{word_header}\n\n**Language:** {language.title()}\n\n**Definition:**\n{definition}\n\n" \
                     f"**Etymology:**\n{etymology.strip()}"
        return_str = re.sub(r"\.mw-parser-output.*", "", return_str)
        double_derived_terms = re.compile(r"[\w\s]+\[edit\].*?\*\*", re.DOTALL)
        return_str = re.sub(double_derived_terms, "\n\n**", return_str)
        return_str = re.sub(r"Derived terms[^:]\n*", "", return_str)
        return_str = re.sub(r"Compounds[^:]\n*", "", return_str)
        return_str = re.sub(r"Synonyms[^:]\n*", "", return_str)
        return '\n' + return_str


    @staticmethod
    def get_derivatives(word, language='latin', misc=False):
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


    @staticmethod
    def get_word_header(word, language):
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

        print(f"Getting {language} etymology for {word}")
        etymology = "Not found"
        if tries > QUOTE_RETRIEVAL_MAX_TRIES:
            return etymology
        if language.lower() == 'tradchinese':
            word = tradify(word)
            language = 'chinese'
        if language.lower() == 'chinese' or language.lower() == 'tradchinese':
            word = tradify(word)
            language_section, soup = my_wiktionary_parser.get_language_header(word, language)
            return my_wiktionary_parser.get_etymology(language_section, language, word).replace(u'\xa0', u' ')
        language_section, soup = my_wiktionary_parser.get_language_header(word, language)
        etymology = my_wiktionary_parser.get_etymology(language_section, language, word).replace(u'\xa0', u' ')
        if etymology == "Not found":
            if tries == 1:
                return self.get_word_etymology(word.upper(), language, tries + 1)
            if word.istitle():
                return self.get_word_etymology(word.lower(), language, tries + 1)
            if word.lower():
                return self.get_word_etymology(word.title(), language, tries + 1)
        return etymology


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
            url = random.choice(CHINESE_WORD_CHOICES)
            print(f"Chose {url.split('/')[0]} for getting a random Chinese word")
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


    @staticmethod
    def case_transform(s, to_lower):
        if to_lower:
            return s.lower()
        else:
            return s


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
        word_defs = self.get_word_definitions(word, language, include_examples)
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


    @staticmethod
    def sort_files(file):
        try:
            return int(''.join([s.strip() for s in file if s.isdigit()]))
        except:
            return hash(file)


    @staticmethod
    def format_reconstructed(language, word):
        return f"Reconstruction:{language.title()}/{word}".replace('*', '')


    @staticmethod
    def word_is_in_wiktionary(word):
        soup = my_wiktionary_parser.get_soup(word)
        return soup and "does not yet have an entry" not in soup


    @staticmethod
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


    @staticmethod
    def _passage_deliminator(text, delimiters=None):
        if delimiters is None:
            delimiters = DELIMITERS
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


    @staticmethod
    def chunks(lst, n):
        """Yield successive n-sized chunks from l."""
        for i in range(0, len(lst), n):
            yield lst[i:i + n]


    @staticmethod
    def get_available_bible_versions():
        """
        Get a list of Bible versions in multiple languages from which we can retrieve passages for the sake of
        linguistic comparison

        :return: a formatted list of bible versions
        """
        return ', '.join(sorted([f"{key.title()}" for key in bible_versions.versions], key=str.lower))


    @staticmethod
    def get_available_bible_versions_lang(lang):
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
            chunks = RobotBrain.chunks(versions, 10)
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


    @staticmethod
    def get_book_and_chapter(book_and_verse):
        book, chapter = "", ""
        if len(book_and_verse.split(" ")) == 4:
            book = "Song of Songs"
            chapter = book_and_verse.split(" ")[3].split(":")[0]
        elif len(book_and_verse.split(" ")) == 3:
            book = " ".join(book_and_verse.split(" ")[:2])
            chapter = book_and_verse[2].split(":")[0]
        elif len(book_and_verse.split(" ")) == 2:
            book = book_and_verse.split(" ")[0]
            print(f"Book: {book}")
            chapter = book_and_verse.split(" ")[1].split(":")[0]
        return book, chapter


    @staticmethod
    def get_verse_range(book, book_and_verse):
        print(f"Book: {book}, Book and Verse: {book_and_verse}")
        verse_range = None
        if book.lower() == "song of songs":
            verse_range = book_and_verse.split(" ")[3].split(":")[1]
        elif len(book_and_verse.split()) == 2:
            verse_range = book_and_verse.split(" ")[1].split(":")[1]
        elif len(book_and_verse.split()) == 3:
            verse_range = book_and_verse.split()[2].split(":")[1]
        print(verse_range)
        if '-' in verse_range:
            begin = int(verse_range.split('-')[0])
            end = int(verse_range.split('-')[1]) + 1
        else:
            begin = int(verse_range)
            end = int(verse_range) + 1
        return [v for v in range(begin, end)]


    def get_bible_verse_by_api_v1(self, book_and_verse, version='kjv'):
        print(f"Getting {book_and_verse} in {version} from v1 API")
        url = f"{GET_BIBLE_LEGACY_BASE_URL}/json?passage={book_and_verse}&version={version}"
        print(f"v1 API endpoint: {url}")
        response = requests.get(url).text.replace(');', '').replace('(', '')
        try:
            content = json.loads(response)
        except:
            return None
        if "NULL" in response:
            return None
        book, chapter = self.get_book_and_chapter(book_and_verse)
        verse_range = self.get_verse_range(book, book_and_verse)
        verses = []
        for verse_nr in verse_range:
            verses.append(
                content['book'][0]['chapter'][str(verse_nr)]["verse"].replace('\n', '').replace(' ;', ';').replace(
                    ' :', ':').replace(' ?', '?'))
        return '\n'.join(verses)


    def get_bible_verse_by_api_v2(self, book_and_verse, version='kjv'):

        book, chapter = self.get_book_and_chapter(book_and_verse)

        url = f"{GET_BIBLE_BASE_URL}/v2/{version}/{getbible_books_to_numbers.mapping[book]}/{chapter}.json"
        print(f"Getting verses {book_and_verse} in {version} from v2 API: {url}")
        response = requests.get(url)
        if response.status_code == 404:
            print(f"Could not find verse {book_and_verse} from v2 API")
            return None
        json_response = json.loads(response.content)
        verse_range = self.get_verse_range(book, book_and_verse)
        verses = []
        for verse_nr in verse_range:
            verses.append(json_response['verses'][verse_nr - 1]['text'].replace('\n', '').replace(' ;', ';').replace(
                ' :', ':').replace(' ?', '?').replace("  ", " "))
        return '\n'.join(verses)


    def get_bible_verse_by_api(self, book_and_verse, version='kjv'):
        """
        Get a Bible verse using the getbible.net API

        :param book_and_verse: the Bible verses (e.g. Romans 3:23) that we wish to retrieve. Note that a range of
        verses, such as Matthew 6:9–13, is permitted.
        :param version: the version of the Bible, such as the KJV or
        the Vulgate, from which we wish to retrieve the verse(s) :return: the passage from the given version of the
        Bible covered by the input verses
        """

        passage = self.get_bible_verse_by_api_v2(book_and_verse, version)
        if not passage:
            print(f"Failed to retrieve {book_and_verse}, trying v1 API")
            passage = self.get_bible_verse_by_api_v1(book_and_verse, version)
        return passage


    def get_bible_verse_from_gateway(self, book_and_verse, version='kjv'):
        """
        Get a Bible verse from www.biblegateway.com.

        :param book_and_verse: the Bible verses (e.g. Romans 3:23) that we wish to retrieve. Note that a range of
        verses, such as Matthew 6:9–13, is permitted.
        :param version: the version of the Bible, such as the KJV or the Vulgate, from which we wish to retrieve the
        verse(s)
        :return: the passage from the given version of the Bible covered by the input verses
        """
        url = f"https://www.biblegateway.com/passage/?search={book_and_verse.replace(' ', '%20')}&version={version}&src=tools"
        print(f"Gateway URL: {url}")
        soup = BeautifulSoup(requests.get(url).text.replace("<!-->", ""),
                             features="html.parser")
        print(soup.prettify())
        chapter = None
        book = None
        if len(book_and_verse.split(" ")) == 4:
            book = "Song of Songs"
            chapter = book_and_verse.split(" ")[3].split(":")[0]
        elif len(book_and_verse.split(" ")) == 3:
            book = " ".join(book_and_verse[:2])
            chapter = book_and_verse[2].split(":")[0]
        elif len(book_and_verse.split(" ")) == 2:
            book = book_and_verse.split(" ")[0]
            chapter = book_and_verse.split(" ")[1].split(":")[0]
            print(f"Book: {book}, chapter: {chapter}")
        verse_range = self.get_verse_range(book.lower(), book_and_verse)
        print(f'Verses to parse: {verse_range}')
        book_abbreviation = abbreviations[book.lower()]
        print(f"Book abbreviation: {book_abbreviation}")
        try:
            verse_rows = []
            for verse_nr in verse_range:
                print(f"Verse num: {verse_nr}")
                verse_rows.extend([x.get_text() for x in soup.find_all('span', {'class': f'text {book_abbreviation}-'
                                                                                         f'{chapter}-{verse_nr}'})])
            passage = "\n".join(verse_rows)
            if not passage:
                return "Not found"
            return passage
        except:
            return "Not found"


    @staticmethod
    def get_wycliffe_verse(verse):
        """
        Get a verse from the Wycliffe Bible
        """
        url = f"https://studybible.info/Wycliffe/{verse}"
        body = requests.get(url).text
        soup = BeautifulSoup(body, features="html.parser")
        passage = soup.find_all("div", {"class": "passage row Wycliffe"})[0]
        [s.extract() for s in soup('sup')]
        return re.sub(r"[\s]{2,}", "\n", passage.get_text().replace('Wycliffe', '').strip())


    def get_bible_verse_studybible(self, verse, version='kjv'):
        url = f"https://studybible.info/{version}/{verse}"
        pass


    def get_bible_verse(self, verse, version='kjv'):
        """
        Get a Bible verse from a given version. This implementation tries multiple sources until one is found which
        can successfully retrieve the given verse in the given version.

        :param verse: the Bible verses (e.g.  Romans 3:23) that we wish to retrieve. Note that a range of verses, such
        as Matthew 6:9–13, is permitted.
        :param version: the version of the Bible, such as the KJV or the Vulgate, from which we wish to retrieve the verse(s)
        :return: the passage from the given version of the Bible covered by the input verses
        """

        original_version = version
        raw_version = version.lower().replace("$", "").replace("#", "").replace("&", "")
        if raw_version not in bible_versions.all_versions:
            language = version.replace("$", "").replace("#", "").replace("&", "")
            print(f"Getting a version from {language}")
            version = lang_to_versions[language.lower()][0]
            if '$' in original_version:
                version = f"Transliterating {version}"
            print(f"Using {version} for {language}")
        print(f"version: {version}")
        middle_chinese = False
        old_chinese = False
        translit = False
        if version[0] == '$':
            version = ''.join(version[1:])
            translit = True
        if version[0] == '#':
            version = ''.join(version[1:])
            translit = False
            middle_chinese = True
        if version[0] == '&':
            version = ''.join(version[1:])
            translit = False
            old_chinese = True
        verse = verse.title()
        print(verse)
        if len(verse.split(" ")) == 3:
            book = " ".join(verse.split(" ")[:2])
            verse_numbers = verse.split(" ")[2]
        else:
            book = verse.split(" ")[0]
            verse_numbers = verse.split(" ")[1]
        print(f"Book: {book}, Verse numbers: {verse_numbers}")
        if version.strip().lower() == 'meiji':
            try:
                return get_meiji_japanese_verses(book.lower(), verse_numbers, translit).strip()
            except:
                traceback.print_exc()
                return "Not found"
        if version.strip().lower() == 'cc':
            try:
                return get_cc_verses(book.lower(), verse_numbers, translit, middle_chinese, old_chinese)
            except:
                traceback.print_exc()
                return "Not found"
        if version.strip().lower() == 'wyc':
            try:
                return self.get_wycliffe_verse(verse).strip()
            except:
                traceback.print_exc()
                return "Not found"
        if version.strip().lower() == 'old_english':
            try:
                return self.get_old_english_verse(verse).strip()
            except:
                traceback.print_exc()
                return "Not found"
        passage = self.get_bible_verse_by_api(verse, version)
        if not passage:
            print(f"API for {version} failed, trying Gateway")
            passage = self.get_bible_verse_from_gateway(verse, version)
        if translit:
            passage = self.transliterate_verse(version, passage, middle_chinese, old_chinese)
        return passage.strip()


    @staticmethod
    def get_random_verse_by_testament(testament):
        """
        Get a random verse from either the Old Testament or the New Testament
        :param testament: can be either "ot" or "nt"
        :return: a random verse
        """
        with open(f"bible_verses_{testament}.txt") as file:
            verses = file.read().split('|')
            return random.choice(verses).title()


    @staticmethod
    def get_gothic_verses_set():
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


    @staticmethod
    def get_random_verse():
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
            print(f"Verse: {verse}, versions: {versions}")
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
                except Exception as e:
                    print(e)
                    return "Failed to retrieve verse. Your target versions may be incompatible. For example, the Gothic Bible contains only the New Testament, while the Westminster Leningrad Codex contains only the Old Testament. There will be no overlapping verses."

        return '\n'.join(translations)


    @staticmethod
    def transliterate_verse(version, text, middle_chinese, old_chinese):
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
            text = transliteration.hebrew.transliterate(text)
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
        if version in KOREAN:
            text = transliteration.korean.transliterate(text)
        if version in JAPANESE:
            text = transliteration.japanese.transliterate(text)
        if version in CHINESE:
            if middle_chinese:
                text = transliteration.middle_chinese.transliterate(text).replace("  ", " ")
            elif old_chinese:
                text = transliteration.old_chinese.transliterate(text).replace("  ", " ")
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
        except Exception as e:
            print(e)
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


    @staticmethod
    def _replace_placeholders(text):
        for key in REVERSE_DELIMITERS_MAP:
            text = text.replace(key, REVERSE_DELIMITERS_MAP[key])
        return text


    @staticmethod
    def _process_basic(text):
        return ['. '.join(s) + '.' for s in list(RobotBrain.chunks(text, 3))]


    @staticmethod
    def _process_mixed(text):
        if ABSOLUTE_DELIMITER in text:
            return RobotBrain._process_absolute(text)
        return RobotBrain._process_text(text)


    @staticmethod
    def _process_absolute(text):
        splitted = text.split(ABSOLUTE_DELIMITER)
        return [w.replace(ABSOLUTE_DELIMITER, "") for w in splitted]


    @staticmethod
    def _process_text(text):
        text = RobotBrain._replace_abbreviation_period(text)
        text = RobotBrain._passage_deliminator(text)
        text = re.sub(r"[\n]{2,}|(\n+\s+){2,}|(\s+\n+){2,}", "\n\n", text)
        first_pass = [s for s in re.split(DELIMITERS_REGEX, text)]
        return [re.sub(REGEX_SUB, '', t) + (first_pass[i + 1] if first_pass[i + 1] != '|' else '') for i, t in
                enumerate(first_pass) if 'LIBRARY' not in t.upper()
                and t.strip().replace('\n', '') != '' and MIN_QUOTES_LENGTH < len(t) < MAX_QUOTES_LENGTH and
                i < len(first_pass) - 1]


    @staticmethod
    def splitkeepsep(s, sep):
        return reduce(lambda acc, elem: acc[:-1] + [acc[-1] + elem] if re.match(elem, sep) else acc + [elem],
                      re.split("(%s)" % re.escape(sep), s), [])


    @staticmethod
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


    @staticmethod
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


    @staticmethod
    def format_name(author):
        return author.title().replace('Of ', 'of ').replace('The ', 'the ').replace(' De ', ' de ')


    def pick_quote_generic(self, quote_dict):
        author = random.choice(list(quote_dict.keys()))
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


    @staticmethod
    def flatten(array):
        return [item for sublist in array for item in sublist]


    @staticmethod
    def find_multi_regex(regexes, passage, case_sensitive):
        if not case_sensitive:
            passage = passage.lower()
        generic_re = re.compile('|'.join(regexes))
        matches = re.findall(generic_re, passage)
        if matches and len(matches) > 0:
            return matches[0]
        else:
            return None


    @staticmethod
    def matching_quote(file, regex, case_sensitive, proces_func):
        quotes = []
        for i, quote in enumerate(file.read()):
            quotes.append(quote)
            return i, quotes, RobotBrain.find_multi_regex(regex,
                                                          re.sub(r"[^\w0-9\s\n]", "", proces_func(quote),
                                                                 case_sensitive))


    @staticmethod
    def unpack(*lst):
        return lst


    @staticmethod
    def remove_accents(input_str):
        if isinstance(input_str, bytes) or isinstance(input_str, bytearray):
            input_str = input_str.decode('utf8')
        nfkd_form = unicodedata.normalize('NFKD', input_str)
        return u"".join([c for c in nfkd_form if not unicodedata.combining(c)])


    def pick_quote(self, files, process_func, word=None, lemmatize=False, case_sensitive=False, chinese=False):
        if word:
            word = self.remove_accents(word).lower() if not case_sensitive else word
            regex_list = []
            if lemmatize:
                try:
                    inflected = self.decliner.decline(word, flatten=True)
                    for form in inflected:
                        regex_list.append(f"\\b{form}\\b")
                except:
                    traceback.print_exc()
                    return -1, "Unknown lemma.", []
            else:
                if chinese:
                    regex_list.append(f"{word}")
                else:
                    regex_list.append(f"\\b{word}\\b")
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
                quotes_list.append((j_index + 1, EOF, i))
                f.seek(0)
            if len(search_quotes) == 0:
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


    @staticmethod
    def get_passage_list_for_file(file, process_func):
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
                i, quote = self.pick_quote(RobotBrain._process_text, word, lemmatize, case_sensitive)
            except Exception as error:
                if self.quote_tries < QUOTE_RETRIEVAL_MAX_TRIES:
                    self.quote_tries += 1
                    i, quote = self.pick_quote(RobotBrain._process_text, word, lemmatize, case_sensitive)
                    return quote
                else:
                    self.quote_tries = 0
                    raise error
        elif "the " + person in self.greek_quotes_dict:
            files = self.greek_quotes_dict["the " + person]
            try:
                i, quote = self.pick_quote(RobotBrain._process_text, word, lemmatize, case_sensitive)
            except Exception as error:
                if self.quote_tries < QUOTE_RETRIEVAL_MAX_TRIES:
                    self.quote_tries += 1
                    i, quote = self.pick_quote(RobotBrain._process_text, word, lemmatize, case_sensitive)
                    return i, quote
                else:
                    self.quote_tries = 0
                    raise error
        else:
            if not person in self.latin_quotes_dict:
                person = "the " + person
            files = self.latin_quotes_dict[person]
            if person == 'the bible':
                i, quote = self.pick_quote(RobotBrain._process_holy_text, word, lemmatize, case_sensitive)
            elif person == 'phrases':
                res = [(i, e) for i, e in
                       enumerate(open(f"{LATIN_TEXTS_PATH}/phrases/phrases.txt").read().split("円"))]
                index = random.randint(0, len(res))
                i = index
                quote = res[i]
                return quote
            else:
                i, quote = self.pick_quote(RobotBrain._process_text, word, lemmatize, case_sensitive)
        return re.sub(r"^[\s]*[\n]+[\s]*", " ", RobotBrain.fix_crushed_punctuation(quote))


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
            i, quote, quotes_list = self.pick_quote(files, RobotBrain._process_absolute, word, lemmatize,
                                                    case_sensitive)
        elif person == 'yogi berra':
            i, quote, quotes_list = self.pick_quote(files, RobotBrain._process_absolute, word, lemmatize,
                                                    case_sensitive)
        elif person == 'the bible':
            i, quote, quotes_list = self.pick_quote(files, RobotBrain._process_holy_text, word, lemmatize,
                                                    case_sensitive)
        elif person == 'phrases':
            i, quote, quotes_list = self.pick_quote(files, RobotBrain._process_absolute, word, lemmatize,
                                                    case_sensitive)
        elif person == 'mommsen':
            files = [f for f in files if 'content' not in f.name]
            index_files = [f for f in files if 'content' in f.name]
            i, quote, quotes_list = self.pick_quote(files, RobotBrain._process_text, word, lemmatize, case_sensitive)
        elif person == 'gibbon':
            i, quote, quotes_list = self.pick_quote(files, RobotBrain._process_mixed, word, lemmatize, case_sensitive)
        elif person in self.chinese_authors:
            i, quote, quotes_list = self.pick_quote(files, RobotBrain._process_text, word, lemmatize, case_sensitive,
                                                    chinese=True)
        else:
            i, quote, quotes_list = self.pick_quote(files, RobotBrain._process_text, word, lemmatize, case_sensitive)
        return i, re.sub(r"^[\s]*[\n]+[\s]*", " ", RobotBrain.sanitize(quote)), quotes_list


    @staticmethod
    def sanitize(quote):
        return RobotBrain.fix_crushed_punctuation(quote)


    @staticmethod
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


    @staticmethod
    def get_shuowen_char_etymology(char):
        explanation = my_wiktionary_parser.get_shuowen(char)
        if not explanation:
            explanation = "Could not find glyph origin in Shuowen"
        return explanation


    @staticmethod
    def shuowen_game():
        char_id = str(random.randint(1, 9833))
        char_url = "http://www.shuowenjiezi.com/result4.php?id=" + char_id
        print(f"URL for shuowen_game: {char_url}")
        soup = BeautifulSoup(requests.get(char_url).content, features="html.parser")
        explanation = soup.find('div', attrs={'class': 'chinese'})
        for div in explanation.find_all("a", {'class': 'isAnyDuanzhu'}):
            div.decompose()
        character = chr(int(
            '0x' + soup.find('span', attrs={'id': 'radical0'})['onclick'].split(',')[0].split('(')[1].replace('\'', ''),
            16))
        pinyin = soup.find('span', attrs={'id': 'rec1'}).text
        return character, explanation.text, pinyin

from functools import reduce
import json
import random
import re
import string
import traceback
import unicodedata

from bs4 import BeautifulSoup
from lang_trans.arabic import arabtex
import requests
import romanize3
from transliterate import translit

from bible_compare import bible_versions, getbible_books_to_numbers
from bible_compare.bible_versions import lang_to_versions
from bible_compare.classical_chinese_bible import get_cc_verses
from bible_compare.gateway_abbreviations import abbreviations
from bible_compare.meiji_japanese_bible import get_meiji_japanese_verses
from bible_compare.old_english_bible import old_english_bible_translation
from constants import GET_BIBLE_LEGACY_BASE_URL, GET_BIBLE_BASE_URL
from robot_brain import RobotBrain
import transliteration.transliteratable_versions

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

# The below are versions of the Bible (some being exclusively New Testament for a variety of language to support my
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


class BibleService:
    """
    Class encapsulating various bot functionality
    """


    def __init__(self):
        pass


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
        book = ''.join(verse.split(":")[0].split()[0]).lower()
        chapter = verse.split(':')[0].split()[1].strip()
        verses = verse.split(':')[1].strip()
        print(f"Old English book: {book}, chapter: {chapter}, verses: {verses}")
        if '-' in verses:
            begin = int(verses.replace(' ', '').split('-')[0])
            end = int(verses.replace(' ', '').split('-')[1])
            verses = [str(i) for i in range(begin, end + 1)]
        else:
            verses = [verses]
        try:
            return '\n'.join(
                [old_english_bible_translation.get_old_english(book, chapter, verse)[book][chapter][verse] for
                 verse in verses])
        except:
            traceback.print_exc()
            return "Not found. Note that Old English translations are available only for John, Luke, Mark, and Matthew."


    @staticmethod
    def get_book_and_chapter(book_and_verse):
        book, chapter = "", ""
        if len(book_and_verse.split(" ")) == 4:
            book = "Song of Songs"
            chapter = book_and_verse.split(" ")[3].split(":")[0]
        elif len(book_and_verse.split(" ")) == 3:
            book = " ".join(book_and_verse[:2])
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
            if '$' in original_version:
                version = f'${version}'
            print(f"Getting a version from {language}")
            version = lang_to_versions[language.lower()][0]
            if '$' in original_version:
                version = f"${version}"
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
            book = " ".join(verse.split()[:2])
            verse_numbers = verse.split(2)
        else:
            book = verse.split(" ")[0]
            verse_numbers = verse.split(" ")[1]
        print(f"Book: {book}, Verse numbers: {verse_numbers}")
        if version.strip().lower() == 'meiji':
            try:
                print("Getting Meiji verses")
                return get_meiji_japanese_verses(book.lower(), verse_numbers).strip()
            except:
                traceback.print_exc()
                return "Not found"
        elif version.strip().lower() == 'cc':
            try:
                return get_cc_verses(book.lower(), verse_numbers, translit, middle_chinese, old_chinese)
            except:
                traceback.print_exc()
                return "Not found"
        elif version.strip().lower() == 'wyc':
            try:
                return self.get_wycliffe_verse(verse).strip()
            except:
                traceback.print_exc()
                return "Not found"
        elif version.strip().lower() == 'old_english':
            return self.get_old_english_verse(verse).strip()
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
            book = random.choice(['john', 'luke', 'mark', 'matthew'])
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

        transliteration.transliteratable_versions.transliterate_verse(version, text, middle_chinese, old_chinese)


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


    @staticmethod
    def _replace_placeholders(text):
        for key in REVERSE_DELIMITERS_MAP:
            text = text.replace(key, REVERSE_DELIMITERS_MAP[key])
        return text


    @staticmethod
    def _process_basic(text):
        return ['. '.join(s) + '.' for s in list(RobotBrain.chunks(text, 3))]


    @staticmethod
    def _process_absolute(text):
        splitted = text.split(ABSOLUTE_DELIMITER)
        return [w.replace(ABSOLUTE_DELIMITER, "") for w in splitted]


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
    def flatten(array):
        return [item for sublist in array for item in sublist]


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

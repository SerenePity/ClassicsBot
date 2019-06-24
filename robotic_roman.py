from markovchain.text import MarkovText
from bs4 import BeautifulSoup
import bible_versions
import old_english_bible.john
import old_english_bible.luke
import old_english_bible.mark
import old_english_bible.matthew
import romanize3
import transliteration.coptic
import transliteration.greek
import transliteration.hebrew
import traceback
import requests
import json
import random
import os
import re
import string
import praw


LATIN_TEXTS_PATH = "latin_texts"
GREEK_TEXTS_PATH = "greek_texts"
OFF_TOPIC_TEXTS_PATH = "off_topic_texts"
PARALLEL_TEXTS_PATH = "parallel"
SUBREDDIT = 'copypasta'
MAX_QUOTES_LENGTH = 800
MIN_QUOTES_LENGTH = 140
QUOTES = ["\"", "'", "“", "\""]
PRAENOMINA = ["C","L","M","P","Q","T","Ti","Sex","A","D","Cn","Sp","M","Ser","Ap","N","V", "K"]
ROMAN_NUMERALS = ["I","II","III","IV","V","VI","VII","VIII","IX","X","XI","XII","XIII","XIV","XV","XVI","XVII","XVIII","XIX","XX","XXI","XXII","XXIII","XXIV","XXV","XXVI","XXVII","XXVIII","XXIX","XXX","XXXI","XXXII","XXXIII","XXXIV","XXXV","XXXVI","XXXVII","XXXVIII","XXXIX","XL","XLI","XLII","XLIII","XLIV","XLV","XLVI","XLVII","XLVIII","XLIX","L","LI","LII","LIII","LIV","LV","LVI","LVII","LVIII","LIX","LX","LXI","LXII","LXIII","LXIV","LXV","LXVI","LXVII","LXVIII","LXIX","LXX","LXXI","LXXII","LXXIII","LXXIV","LXXV","LXXVI","LXXVII","LXXVIII","LXXIX","LXXX","LXXXI","LXXXII","LXXXIII","LXXXIV","LXXXV","LXXXVI","LXXXVII","LXXXVIII","LXXXIX","XC","XCI","XCII","XCIII","XCIV","XCV","XCVI","XCVII","XCVIII","XCIX","C","CC","CCC","CD","D","DC","DCC","DCCC","CM","M"]
ABBREVIATIONS = PRAENOMINA + [n.lower() for n in PRAENOMINA] + ["Kal", "kal", "K", "CAP", "COS", "cos", "Cos", "ann"] + ROMAN_NUMERALS + list(string.ascii_lowercase) + list(string.ascii_uppercase)
DELIMITERS = [".", "?", "!", "...", ". . .", ".\"", "\.'", "?\"", "?'", "!\"", "!'"]
PARALLEL_DELIMITERS = ["."]
DELIMTERS_MAP = {'.': '%', '?': '#', '!': '$'}
REVERSE_DELIMITERS_MAP = {'%': '.', '#': '?', '$': '!', '^': '...'}
REGEX_SUB = re.compile(r"\n\n|\[|\]|\(\)")
DELIMITERS_REGEX = "(\.\"|\.'|\.|\?|!|\^|\|)"
BIBLE_DELIMITERS = "[0-9]+"
ABSOLUTE_DELIMITER = "|"
GETBIBLE_VERSIONS = set(['aov', 'albanian', 'amharic', 'hsab', 'arabicsv', 'peshitta', 'easternarmenian', 'westernarmenian', 'basque', 'breton', 'bulgarian1940', 'chamorro', 'cns', 'cnt', 'cus', 'cut', 'bohairic', 'coptic', 'sahidic', 'croatia', 'bkr', 'cep', 'kms', 'nkb', 'danish', 'statenvertaling', 'kjv', 'akjv', 'asv', 'basicenglish', 'douayrheims', 'wb', 'weymouth', 'web', 'ylt', 'esperanto', 'estonian', 'finnish1776', 'pyharaamattu1933', 'pyharaamattu1992', 'darby', 'ls1910', 'martin', 'ostervald', 'georgian', 'elberfelder', 'elberfelder1905', 'luther1545', 'luther1912', 'schlachter', 'gothic', 'moderngreek', 'majoritytext', 'byzantine', 'textusreceptus', 'text', 'tischendorf', 'westcotthort', 'westcott', 'lxxpar', 'lxx', 'lxxunaccentspar', 'lxxunaccents', 'aleppo', 'modernhebrew', 'bhsnovowels', 'bhs', 'wlcnovowels', 'wlc', 'codex', 'karoli', 'giovanni', 'riveduta', 'kabyle', 'korean', 'newvulgate', 'latvian', 'lithuanian', 'manxgaelic', 'maori', 'judson', 'bibelselskap', 'almeida', 'potawatomi', 'rom', 'cornilescu', 'makarij', 'synodal', 'zhuromsky', 'gaelic', 'valera', 'rv1858', 'sse', 'swahili', 'swedish', 'tagalog', 'tamajaq', 'thai', 'tnt', 'turkish', 'ukranian', 'uma', 'vietnamese', 'wolof', 'xhosa'])
COPTIC = ['bohairic', 'sahidic', 'coptic']
ARAMAIC = ['peshitta']
HEBREW = ['aleppo', 'modernhebrew', 'bhsnovowels', 'bhs', 'wlcnovowels', 'wlc', 'codex']
ARABIC = ['arabicsv']
GREEK = ['moderngreek', 'majoritytext', 'byzantine', 'textusreceptus', 'text', 'tischendorf', 'westcotthort', 'westcott', 'lxxpar', 'lxx', 'lxxunaccentspar', 'lxxunaccents']
RUSSIAN = ['makarij', 'synodal', 'zhuromsky']


QUOTE_RETRIEVAL_MAX_TRIES = 3
COMMANDS = ["Get random quote by author:            '>qt [-t] <author> (-t to transliterate) | As <author> said:'",
            "Generate sentence by author:           '>markov [-t] <author> (-t to transliterate) | As <author> allegedly said:'",
            "List available Latin authors:          '>latinauthors'",
            "Retrieve random Latin quote:           '>latinquote'",
            "Transliterate input:                   '>tr <input>'",
            "List available Greek authors:          '>greekauthors'",
            "Retrieve random Greek quote:           '>greekquote'",
            "Start Latin game:                      '>latingame'",
            "Start Greek game:                      '>greekgame'",
            "Guess answer:                          '<answer>'",
            "End game:                              '>giveup'",
            "Join game:                             '>join <game owner>'",
            "Owify quote from author:               '>owo <author>",
            "Parallel Gothic Bible:                 '>ulfilas <translation version>",
            "Get available Bible versions:          '>bibleversions [<lang>]'",
            "Bible compare ($ for romanization):    '>biblecompare [<verse>] [$]<translation1> [$]<translation2>'",
            "Quote for parallel text:               '>parallel <work/author>'",
            "Texts/authors for parallel command:    '>listparallel'",
            "Help:                                  '>HELPME'"]

class RoboticRoman():

    def __init__(self):
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

    def help_command(self):
        return '```' + '\n'.join(COMMANDS) + '```'

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
            print(quote)
            verse = re.findall(r"[0-9]*\w+\s[0-9]+:[0-9]+", quote)[0]
            book = verse.split()[0]
            print(book)
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
        return ', '.join([f"{key.title()}" for key in bible_versions.versions])

    def get_available_bible_versions_lang(self, lang):
        versions = bible_versions.versions[lang.lower()]
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
        print("In get_old_english_verse")
        book = ''.join(verse.split(":")[0].split()[:-1]).lower()
        chapter = verse.split(':')[0].split()[-1].strip()
        verses = verse.split(':')[1].strip()
        if '-' in verses:
            begin = int(verses.replace(' ', '').split('-')[0])
            end = int(verses.replace(' ', '').split('-')[1])
            verses = [str(i) for i in range(begin, end + 1)]
            print(verses)
        else:
            verses = [verses]

        print("VERSE: " + verse)
        print(f"Book: {book}, Chapter: {chapter}, Verse: {verse}")
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
        print("URL: " + url)
        book = int(verse.split(':')[0].split()[-1])
        chapters = verse.split(':')[1]
        print(f"Book: {book}")
        if '-' in chapters:
            begin = int(chapters.replace(' ', '').split('-')[0])
            end = int(chapters.replace(' ', '').split('-')[1])
            chapters = [str(i) for i in range(begin, end + 1)]
            print(chapters)
        else:
            chapters = [chapters]
        response = requests.get(url).text.replace(');', '').replace('(', '')
        content = json.loads(response)
        print(content)
        verses = []
        try:
            for chapter in chapters:
                verses.append(content['book'][0]['chapter'][chapter]['verse'].replace('\n', ''))
            print(verses)
            passage = ' '.join(verses)
        except:
            print("Verse: " + verse)
            passage = "Not found"
            traceback.print_exc()
        if version.strip().lower() == 'gothic':
            passage = re.sub(r"\[\w+\]\s", '', passage)
        if not passage or len(passage.strip()) == 0:
            passage = "Not found"
        print(f"Passage length: {len(passage)}")
        print(passage)
        return passage

    def get_bible_verse_from_gateway(self, verse, version='kjv'):
        url = f"https://www.biblegateway.com/passage/?search={verse}&version={version}&src=tools"
        response = requests.get(url)
        print(url)
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
            print(passage)
            passage = re.sub(r"^\s*[0-9]+\s*", "", passage)
            passage = re.sub(r"\s*[0-9]+\s*", "\n", passage)
            passage = re.sub(r"[\s]{2,}", "\n", passage)
            passage = re.sub(r"[0-9]+(\w)", "\1", passage)
        except:
            passage = "Not found"
        return passage.replace('\t', ' ')

    def get_bible_verse(self, verse, version='kjv'):
        translit = False
        if version[0] == '$':
            version = version[1:]
            translit = True
        verse = verse.title()
        passage = "Not found"
        if version.strip().lower() == 'old_english':
            print("Getting OE version")
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
        print(versions)
        versions = [version.strip().lower() for version in versions]
        if 'gothic' in versions:
            verse = self.get_gothic_verse()
        elif 'old_english' in versions:
            book = random.choice(['jn', 'lk', 'mk', 'mt'])
            oe_dict = self.old_english_dict[book]
            chapter = random.choice(list(oe_dict.keys()))
            verse = random.choice(list(oe_dict[chapter].keys()))
            verse = f"{book} {chapter}:{verse}"
            print("OE verse: " + verse)
        elif 'gothic' in versions and 'old_english' in versions:
            gothic_verses = self.get_gothic_verses_set()
            oe_verses = self.get_old_english_verses_set()
            print(gothic_verses)
            print(oe_verses)
            intersection = gothic_verses.intersection(oe_verses)
            verse = random.choice(list(intersection))
        else:
            verse = self.get_random_verse()
        try:
            translations = [f"**{verse.title()}** - {self.get_bible_verse(verse, version)}" for version in versions]
            if "Not found" in ' '.join([t.split(' - ')[1].strip() for t in translations]):
                print("Failed. Trying New Testament")
                verse = self.get_random_verse_by_testament("nt")
                translations = [f"**{verse.title()}** - {self.get_bible_verse(verse, version)}" for version in versions]
                if "Not found" in ' '.join([t.split(' - ')[1].strip() for t in translations]):
                    verse = self.get_random_verse_by_testament("ot")
                    print("Failed. Trying Old Testament")
                    translations = [f"**{verse.title()}** - {self.get_bible_verse(verse, version)}" for version in
                                    versions]
        except:
            verse = self.get_random_verse_by_testament("nt")
            print("Failed. Trying New Testament")
            try:
                translations = [f"**{verse.title()}** - {self.get_bible_verse(verse, version)}" for version in versions]
            except:
                try:
                    verse = self.get_random_verse_by_testament("ot")
                    print("Failed. Trying Old Testament")
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
            print(quote)
            verse = re.findall(r"[0-9]*\w+\s[0-9]+:[0-9]+", quote)[0]
            book = verse.split()[0]
            print(book)
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

    def _process_text(self, text):
        text = self._replace_abbreviation_period(text.replace('...', '^'))
        text = self._passage_deliminator(text)
        first_pass = [s for s in re.split(DELIMITERS_REGEX, text)]
        return [re.sub(REGEX_SUB, '', t) + (first_pass[i+1] if first_pass[i+1] != '|' else '') for i,t in
                enumerate(first_pass) if 'LATIN' not in t.upper() and 'LIBRARY' not in t.upper()
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
            print(author)
            self.load_quotes(author)

        for grecian in self.greek_quotes_dict:
            print(grecian)
            self.load_greek_quotes(grecian)

        for person in self.off_topic_quotes_dict:
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
        return f"{self.random_quote(author)}\n\t―{self.format_name(author)}"

    def random_quote(self, person):
        print(person)
        if person.strip().lower() == 'reddit':
            return self.reddit_quote(SUBREDDIT)
        if person in self.greek_quotes_dict:
            f = random.choice(self.greek_quotes_dict[person])
            try:
                quote = random.choice(self._process_text(f.read()))
            except Exception as error:
                if self.quote_tries < QUOTE_RETRIEVAL_MAX_TRIES:
                    self.quote_tries += 1
                    return self.random_quote(person)
                else:
                    self.quote_tries = 0
                    raise error
        elif person in self.off_topic_authors:
            f = random.choice(self.off_topic_quotes_dict[person])
            quote = random.choice(self._process_text(f.read()))
        elif 'parallel_' in person:
            f = random.choice(self.parallel_quotes_dict[person.replace('parallel_', '')])
            quote = random.choice(self._process_parallel(f.read()))
            print("Parallel quote: " + quote)
        else:
            f = random.choice(self.quotes_dict[person])
            if person == 'the bible':
                quote = random.choice(self._process_holy_text(f.read()))
            else:
                quote = random.choice(self._process_text(f.read()))
        f.seek(0)
        return re.sub(r"^[\s]*[\n]+[\s]*", " ", self.fix_crushed_punctuation(self._replace_placeholders(quote)))

    def fix_crushed_punctuation(self, text):
        text = re.sub(r"(\w)\.([^\s])", r"\1. \2", text)
        text = re.sub(r"(\w);([^\s])", r"\1; \2", text)
        text = re.sub(r"(\w)\?([^\s])", r"\1? \2", text)
        text = re.sub(r"(\w)!([^\s])", r"\1! \2", text)
        return text

    def pick_greek_quote(self):
        author = random.choice(list(self.greek_quotes_dict.keys()))
        return f"{self.random_quote(author)}\n\t―{self.format_name(author)}"

    def load_model(self, author):
        return MarkovText.from_file(f"markov_models/{author}/{author}_markov.json")

    def make_sentence(self, author):
        if author.strip().lower() == 'reddit':
            return "Just to be clear, I'm not a professional \"quote maker\". I'm just an atheist teenager who greatly " \
                   "values his intelligence and scientific fact over any silly fiction book written 3,500 years ago. " \
                   "That being said, I am open to any and all criticism.\n\n\"In this moment, I am euphoric. " \
                   "Not because of any phony god's blessing. But because, I am englightened by my intelligence.\" - Aalewis"
        if not os.path.isfile(f"markov_models/{author}/{author}_markov.json"):
            path = f"{LATIN_TEXTS_PATH}/{author}" if author in self.authors else f"{GREEK_TEXTS_PATH}/{author}"
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
from markovchain.text import MarkovText
from bs4 import BeautifulSoup
#import romanize3
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
SUBREDDIT = 'copypasta'
MAX_QUOTES_LENGTH = 800
MIN_QUOTES_LENGTH = 140
QUOTES = ["\"", "'", "“", "\""]
PRAENOMINA = ["C","L","M","P","Q","T","Ti","Sex","A","D","Cn","Sp","M","Ser","Ap","N","V", "K"]
ROMAN_NUMERALS = ["I","II","III","IV","V","VI","VII","VIII","IX","X","XI","XII","XIII","XIV","XV","XVI","XVII","XVIII","XIX","XX","XXI","XXII","XXIII","XXIV","XXV","XXVI","XXVII","XXVIII","XXIX","XXX","XXXI","XXXII","XXXIII","XXXIV","XXXV","XXXVI","XXXVII","XXXVIII","XXXIX","XL","XLI","XLII","XLIII","XLIV","XLV","XLVI","XLVII","XLVIII","XLIX","L","LI","LII","LIII","LIV","LV","LVI","LVII","LVIII","LIX","LX","LXI","LXII","LXIII","LXIV","LXV","LXVI","LXVII","LXVIII","LXIX","LXX","LXXI","LXXII","LXXIII","LXXIV","LXXV","LXXVI","LXXVII","LXXVIII","LXXIX","LXXX","LXXXI","LXXXII","LXXXIII","LXXXIV","LXXXV","LXXXVI","LXXXVII","LXXXVIII","LXXXIX","XC","XCI","XCII","XCIII","XCIV","XCV","XCVI","XCVII","XCVIII","XCIX","C","CC","CCC","CD","D","DC","DCC","DCCC","CM","M"]
ABBREVIATIONS = PRAENOMINA + [n.lower() for n in PRAENOMINA] + ["Kal", "kal", "K", "CAP", "COS", "cos", "Cos", "ann"] + ROMAN_NUMERALS + list(string.ascii_lowercase) + list(string.ascii_uppercase)
DELIMITERS = [".", "?", "!", "...", ". . .", ".\"", "\.'", "?\"", "?'", "!\"", "!'"]
DELIMTERS_MAP = {'.': '%', '?': '#', '!': '$'}
REVERSE_DELIMITERS_MAP = {'%': '.', '#': '?', '$': '!', '^': '...'}
REGEX_SUB = re.compile(r"\n\n|\[|\]|\(\)")
DELIMITERS_REGEX = "(\.\"|\.'|\.|\?|!|\^|\|)"
BIBLE_DELIMITERS = "[0-9]+"
ABSOLUTE_DELIMITER = "|"
GETBIBLE_VERSIONS = set(['aov', 'albanian', 'amharic', 'hsab', 'arabicsv', 'peshitta', 'easternarmenian', 'westernarmenian', 'basque', 'breton', 'bulgarian1940', 'chamorro', 'cns', 'cnt', 'cus', 'cut', 'bohairic', 'coptic', 'sahidic', 'croatia', 'bkr', 'cep', 'kms', 'nkb', 'danish', 'statenvertaling', 'kjv', 'akjv', 'asv', 'basicenglish', 'douayrheims', 'wb', 'weymouth', 'web', 'ylt', 'esperanto', 'estonian', 'finnish1776', 'pyharaamattu1933', 'pyharaamattu1992', 'darby', 'ls1910', 'martin', 'ostervald', 'georgian', 'elberfelder', 'elberfelder1905', 'luther1545', 'luther1912', 'schlachter', 'gothic', 'moderngreek', 'majoritytext', 'byzantine', 'textusreceptus', 'text', 'tischendorf', 'westcotthort', 'westcott', 'lxxpar', 'lxx', 'lxxunaccentspar', 'lxxunaccents', 'aleppo', 'modernhebrew', 'bhsnovowels', 'bhs', 'wlcnovowels', 'wlc', 'codex', 'karoli', 'giovanni', 'riveduta', 'kabyle', 'korean', 'newvulgate', 'vulgate', 'latvian', 'lithuanian', 'manxgaelic', 'maori', 'judson', 'bibelselskap', 'almeida', 'potawatomi', 'rom', 'cornilescu', 'makarij', 'synodal', 'zhuromsky', 'gaelic', 'valera', 'rv1858', 'sse', 'swahili', 'swedish', 'tagalog', 'tamajaq', 'thai', 'tnt', 'turkish', 'ukranian', 'uma', 'vietnamese', 'wolof', 'xhosa'])
QUOTE_RETRIEVAL_MAX_TRIES = 3
COMMANDS = ["Get random quote by author:   'As <author> said:'",
            "Generate sentence by author:  'As <author> allegedly said:'",
            "List available Latin authors: '>latinauthors'",
            "Retrieve random Latin quote:  '>latinquote'",
            "List available Greek authors: '>greekauthors'",
            "Retrieve random Greek quote:  '>greekquote'",
            "Start Latin game:             '>latingame'",
            "Start Greek game:             '>greekgame'",
            "Guess answer:                 '<answer>'",
            "End game:                     '>giveup'",
            "Join game:                    '>join <game owner>'",
            "Owify quote from author:      '>owo <author>",
            "Parallel Gothic Bible:        '>ulfilas <translation version>",
            "Bible compare:                '>biblecompare [<verse>] <translation1> <translation2>'",
            "Help:                         '>HELPME'"]

class RoboticRoman():

    def __init__(self):
        self.quotes_dict = dict()
        self.greek_quotes_dict = dict()
        self.off_topic_quotes_dict = dict()
        self.markov_dict = dict()
        self.reddit = praw.Reddit(client_id=os.environ['reddit_client_id'],
                                  client_secret=os.environ['reddit_secret'],
                                  user_agent='user agent')
        self.authors = list(set([f.split('.')[0].replace('_',' ') for f in os.listdir(LATIN_TEXTS_PATH)]))
        self.greek_authors = list(set([f.split('.')[0].replace('_',' ') for f in os.listdir(GREEK_TEXTS_PATH)]))
        self.off_topic_authors = list(set([f.split('.')[0].replace('_',' ') for f in os.listdir(OFF_TOPIC_TEXTS_PATH)]))
        self.quote_tries = 0
        for author in self.authors:
            print(author)
            self.quotes_dict[author] = []

        for grecian in self.greek_authors:
            print(grecian)
            self.greek_quotes_dict[grecian] = []

        for writer in self.off_topic_authors:
            print(writer)
            self.off_topic_quotes_dict[writer] = []

    def help_command(self):
        return '```' + '\n'.join(COMMANDS) + '```'


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

    def _passage_deliminator(self, text):
        cur_sentence_len = 0
        prev_delimiter_pos = 0
        prev_delimiter = ""
        final_sentence = []

        unclosed_paren = False
        for i,c in enumerate(text):
            cur_sentence_len += 1
            if c in DELIMITERS:
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

    def get_bible_verse_by_api(self, verse, version='kjv'):
        url = f"https://getbible.net/json?passage={verse}&version={version}"
        print("URL: " + url)
        chapter = verse.split(':')[1]
        book = verse.split(':')[0].split()[1]
        response = requests.get(url).text.replace(');', '').replace('(', '')
        content = json.loads(response)
        print(content)
        try:
            passage = content['book'][0]['chapter'][chapter]['verse'].replace('\n', '')
        except:
            print("Verse: " + verse)
            print("Book: " + book)
            passage = content['version']['16']['book'][0]['chapter'][chapter]['verse'].replace('\n', '')
        if version.strip().lower() == 'gothic':
            passage = re.sub(r"\[\w+\]\s", '', passage)
        if not passage or len(passage.strip()) == 0:
            passage = "Not found"
        return passage

    def get_bible_verse_from_gateway(self, verse, version='kjv'):
        url = f"https://www.biblegateway.com/passage/?search={verse}&version={version}&src=tools"
        response = requests.get(url)
        print(url)
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
        passage = re.sub(r"^\s*[0-9]+\s*", "", passage.get_text())
        passage = re.sub(r"[\s]{2,}", " ", passage)
        passage = re.sub(r"[0-9]+(\w)", "\1", passage)
        return passage.replace('\n', '')

    def get_bible_verse(self, verse, version='kjv'):
        if version.strip().lower() in GETBIBLE_VERSIONS:
            try:
                passage = self.get_bible_verse_by_api(verse, version)
            except:
                passage = self.get_bible_verse_from_gateway(verse, version)
        else:
            passage = self.get_bible_verse_from_gateway(verse, version)
        return passage

    def get_random_verse_by_testament(self, testament):
        verses = open(f"bible_verses_{testament}.txt").read().split('|')
        return random.choice(verses)

    def get_random_verse(self):
        verses = open(f"bible_verses.txt").read().split('|')
        return random.choice(verses)

    def bible_compare_random_verses(self, version1, version2):
        verse = self.get_random_verse()
        try:
            translation1 = f"{verse} - {self.get_bible_verse(verse, version1)}"
            translation2 = f"{verse} - {self.get_bible_verse(verse, version2)}"
        except:
            verse = self.get_random_verse_by_testament("nt")
            try:
                translation1 = f"{verse} - {self.get_bible_verse(verse, version1)}"
                translation2 = f"{verse} - {self.get_bible_verse(verse, version2)}"
            except:
                try:
                    verse = self.get_random_verse_by_testament("ot")
                    translation1 = f"{verse} - {self.get_bible_verse(verse, version1)}"
                    translation2 = f"{verse} - {self.get_bible_verse(verse, version2)}"
                except:
                    return "Failed to retrieve verse. Your target versions may be incompatible (for example, the Gothic Bible contains only the New Testament, while the Westminster Leningrad Codex contains only the Old Testament. There will be no overlapping verses."
        return '\n'.join([translation1, translation2])

    def bible_compare(self, verse, version1, version2):
        try:
            translation1 = f"{verse} - {self.get_bible_verse(verse, version1)}"
            translation2 = f"{verse} - {self.get_bible_verse(verse, version2)}"
        except:
            return "Failed to retrieve verse. One of your target versions may not contain the requested verse (for example, the Gothic Bible only contains the New Testament, and so requesting an Old Testament verse will fail"
        return '\n'.join([translation1, translation2])

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

    def bible_compare_random(self, version1, version2):
        if 'gothic' in [version1.strip().lower(), version2.strip().lower()]:
            verse = self.get_gothic_verse()
        else:
            verse = self.get_random_verse()
        return self.bible_compare(verse, version1, version2)

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

    def format_name(self, author):
        return author.title().replace('Of ', 'of ').replace('The ', 'the ').replace(' De ',
                                                                        ' de ')
    def pick_random_quote(self):
        author = random.choice(list(self.quotes_dict.keys()))
        return f"{self.random_quote(author)}\n\t―{self.format_name(author)}"

    def random_quote(self, person):
        print(person)
        if person.strip().lower() == 'reddit':
            post = self.reddit.subreddit(SUBREDDIT).random()
            # print(post.selftext)
            body = post.selftext
            if len(body) > 2000:
                body = body[:1995] + "..."
            return body
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
        else:
            f = random.choice(self.quotes_dict[person])
            if person == 'the bible':
                quote = random.choice(self._process_holy_text(f.read()))
            else:
                quote = random.choice(self._process_text(f.read()))
        f.seek(0)
        return re.sub(r"^[\s]*[\n]+[\s]*", " ", self._fix_unclosed_quotes(self._replace_placeholders(quote)))

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
        return self.load_model(author)(max_length=MAX_QUOTES_LENGTH)

    def train_model(self, author, author_path):
        model = MarkovText()
        for file in os.listdir(author_path):
            with open(author_path + '/' + file, encoding="utf8") as fp:
                model.data(fp.read())
        if not os.path.exists(f"markov_models/{author}"):
            os.mkdir(f"markov_models/{author}")
        model.save(f"markov_models/{author}/{author}_markov.json")
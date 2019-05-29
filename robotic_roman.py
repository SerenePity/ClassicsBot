from markovchain.text import MarkovText
import random
import os
import re

LATIN_TEXTS_PATH = "latin_texts"
GREEK_TEXTS_PATH = "greek_texts"
MAX_QUOTES_LENGTH = 500
MIN_QUOTES_LENGTH = 20
PRAENOMINA = ["C","L","M","P","Q","T","Ti","Sex","A","D","Cn","Sp","M","Ser","Ap","N","V", "K"]
ROMAN_NUMERALS = ["I","II","III","IV","V","VI","VII","VIII","IX","X","XI","XII","XIII","XIV","XV","XVI","XVII","XVIII","XIX","XX","XXI","XXII","XXIII","XXIV","XXV","XXVI","XXVII","XXVIII","XXIX","XXX","XXXI","XXXII","XXXIII","XXXIV","XXXV","XXXVI","XXXVII","XXXVIII","XXXIX","XL","XLI","XLII","XLIII","XLIV","XLV","XLVI","XLVII","XLVIII","XLIX","L","LI","LII","LIII","LIV","LV","LVI","LVII","LVIII","LIX","LX","LXI","LXII","LXIII","LXIV","LXV","LXVI","LXVII","LXVIII","LXIX","LXX","LXXI","LXXII","LXXIII","LXXIV","LXXV","LXXVI","LXXVII","LXXVIII","LXXIX","LXXX","LXXXI","LXXXII","LXXXIII","LXXXIV","LXXXV","LXXXVI","LXXXVII","LXXXVIII","LXXXIX","XC","XCI","XCII","XCIII","XCIV","XCV","XCVI","XCVII","XCVIII","XCIX","C","CC","CCC","CD","D","DC","DCC","DCCC","CM","M"]
ABBREVIATIONS = PRAENOMINA + [n.lower() for n in PRAENOMINA] + ["Kal", "kal", "K", "CAP", "COS", "cos", "Cos"] + ROMAN_NUMERALS
REGEX_SUB = re.compile(r"\n\n|\[|\]|\(\)")
DELIMITERS_REGEX = "(\.\"|\.'|\.|\?|!)"
BIBLE_DELIMITERS = "[0-9]+"
COMMANDS = ["Get random quote by author:   'As <author> said:'",
            "Generate sentence by author:  'As <author> allegedly said:'",
            "List available Latin authors: '>latinauthors'",
            "Retrieve random Latin quote:  '>latinquote'",
            "List available Greek authors: '>greekauthors'",
            "Retrieve random Greek quote:  '>greekquote'",
            "Help:                         '>HELPME'"]

class RoboticRoman():

    def __init__(self):
        self.quotes_dict = dict()
        self.greek_quotes_dict = dict()
        self.markov_dict = dict()
        self.authors = [f.path.split('/')[-1] for f in os.scandir(LATIN_TEXTS_PATH) if f.is_dir() and not f.path.split('/')[-1].startswith('.')]
        self.greek_authors = list(set([f.split('.')[0].replace('_',' ') for f in os.listdir(GREEK_TEXTS_PATH)]))
        for author in self.authors:
            print(author)
            self.quotes_dict[author] = []

        for grecian in self.greek_authors:
            print(grecian)
            self.greek_quotes_dict[grecian] = []

    def help_command(self):
        return '```' + '\n'.join(COMMANDS) + '```'

    def _process_text(self, text):
        first_pass = [s for s in re.split(DELIMITERS_REGEX, self._replace_abbreviation_period(text))]
        return [re.sub(REGEX_SUB, '', t).strip().replace('%','.') + first_pass[i+1] for i,t in
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

    def format_name(self, author):
        return author.title().replace('Of ', 'of ').replace('The ', 'the ').replace(' De ',
                                                                        ' de ')
    def pick_random_quote(self):
        author = random.choice(list(self.quotes_dict.keys()))
        return f"{self.random_quote(author)}\n\t―{self.format_name(author)}"

    def random_quote(self, person):
        if person in self.greek_quotes_dict:
            f = random.choice(self.greek_quotes_dict[person])
            quote = random.choice(self._process_text(f.read()))
            #self.load_greek_quotes(person)
        else:
            f = random.choice(self.quotes_dict[person])
            if person == 'the bible':
                quote = random.choice(self._process_holy_text(f.read()))
            else:
                quote = random.choice(self._process_text(f.read()))
            #self.load_quotes(person)
        f.seek(0)
        return quote

    def pick_greek_quote(self):
        author = random.choice(list(self.greek_quotes_dict.keys()))
        return f"{self.random_quote(author)}\n\t―{self.format_name(author)}"

    def load_model(self, author):
        return MarkovText.from_file(f"markov_models/{author}/{author}_markov.json")

    def make_sentence(self, person):
        return self.load_model(person)(max_length=MAX_QUOTES_LENGTH)

    def train_model(self, author, author_path):
        model = MarkovText()
        for file in os.listdir(author_path):
            with open(author_path + '/' + file, encoding="utf8") as fp:
                model.data(fp.read())
        if not os.path.exists(f"markov_models/{author}"):
            os.mkdir(f"markov_models/{author}")
        model.save(f"markov_models/{author}/{author}_markov.json")

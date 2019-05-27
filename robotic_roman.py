from markovchain.text import MarkovText
import random
import os
import re

LATIN_TEXTS_PATH = "latin_texts"
GREEK_TEXTS_PATH = "greek_texts"
PRAENOMINA = ["C","L","M","P","Q","T","Ti","Sex","A","D","Cn","Sp","M","Ser","Ap","N","V", "K"]
ROMAN_NUMERALS = ["I","II","III","IV","V","VI","VII","VIII","IX","X","XI","XII","XIII","XIV","XV","XVI","XVII","XVIII","XIX","XX","XXI","XXII","XXIII","XXIV","XXV","XXVI","XXVII","XXVIII","XXIX","XXX","XXXI","XXXII","XXXIII","XXXIV","XXXV","XXXVI","XXXVII","XXXVIII","XXXIX","XL","XLI","XLII","XLIII","XLIV","XLV","XLVI","XLVII","XLVIII","XLIX","L","LI","LII","LIII","LIV","LV","LVI","LVII","LVIII","LIX","LX","LXI","LXII","LXIII","LXIV","LXV","LXVI","LXVII","LXVIII","LXIX","LXX","LXXI","LXXII","LXXIII","LXXIV","LXXV","LXXVI","LXXVII","LXXVIII","LXXIX","LXXX","LXXXI","LXXXII","LXXXIII","LXXXIV","LXXXV","LXXXVI","LXXXVII","LXXXVIII","LXXXIX","XC","XCI","XCII","XCIII","XCIV","XCV","XCVI","XCVII","XCVIII","XCIX","C","CC","CCC","CD","D","DC","DCC","DCCC","CM","M"]
ABBREVIATIONS = PRAENOMINA + [n.lower() for n in PRAENOMINA] + ["Kal", "kal", "K", "CAP", "COS", "cos", "Cos"] + ROMAN_NUMERALS
REGEX_SUB = re.compile(r"\n\n|\[|\]|\(\)")
DELIMITERS_REGEX = "(\.\"|\.'|\.|\?|!)"
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
                 and t.strip().replace('\n','') != '' and len(t) > 20 and len(t) < 320 and i < len(first_pass) - 1]

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
            self.train_model(author)
            self.markov_dict[author] = f"markov_models/{author}/{author}_markov.json"
    """

    def load_greek_quotes(self, author):
        author_dir = author.replace(' ', '_')
        author_path = f"{GREEK_TEXTS_PATH}/{author_dir}/"
        for file in os.listdir(author_path):
            if file.endswith('.txt'):
                self.greek_quotes_dict[author].append(open(file))

    def load_quotes(self, author):
        self.quotes_dict[author] = []
        author_path = f"{LATIN_TEXTS_PATH}/{author}/"
        for file in os.listdir(author_path):
            if file.endswith('.txt'):
                self.quotes_dict[author].append(open(f"{author_path}/{file}"))

    def format_name(self, author):
        return author.title().replace('Of ', 'of ').replace('The ', 'the ').replace(' De ',
                                                                        ' de ')
    def pick_random_quote(self):
        author = random.choice(list(self.quotes_dict.keys()))
        return f"{self.random_quote(author)}\n\t--{self.format_name(author)}"

    def random_quote(self, person):
        if person in self.greek_quotes_dict:
            return random.choice(self._process_text(self.greek_quotes_dict[person].read()))
        return random.choice(self._process_text(self.quotes_dict[person].read()))

    def pick_greek_quote(self):
        author = random.choice(list(self.greek_quotes_dict.keys()))
        return f"{self.random_quote(author)}\n\t--{self.format_name(author)}"

    def train_model(self, author):
        markov = MarkovText()
        markov.save(f"markov_models/{author}/{author}_markov.json")
        return markov

    def make_sentence(self, person):
        return self.train_model(person)(max_length=320)

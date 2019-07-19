from latin_word_picker.pie_latin import pie
from latin_word_picker.meissner_latin import meissner
from latin_word_picker.medieval_latin import medieval
import random

complete = list(pie.union(meissner, medieval))

def pick_word():
    return random.choice(complete)

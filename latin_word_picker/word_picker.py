from latin_word_picker.pie_latin import pie
from latin_word_picker.meissner_latin import meissner
import random

complete = list(pie.union(meissner))
"""
for i in range(100):
    print(random.choice(list(complete)))
"""

def pick_word():
    return random.choice(complete)

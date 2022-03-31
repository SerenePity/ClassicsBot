from bs4 import BeautifulSoup
import requests

from bible_books_english_to_cc import english_to_cc
from transliteration.mandarin import transliterate


def get_cc_verses(book, verses, translit=False):
    if "-" in verses:
        chapter = verses.split(":")[0].strip()
        verse_range = verses.split(":")[1]
        begin = int(verse_range.split("-")[0])
        end = int(verse_range.split("-")[1])
        passage = []
        for verse in range(begin, end):
            passage.append(get_cc_verse(book, chapter + ":" + str(verse), translit))
        return "\n".join(passage)
    else:
        return get_cc_verse(book, verses, translit)


def get_cc_verse(book, verse, translit=False):
    print(f'book: {book}, verse: {verse}')
    chinese_book = english_to_cc[book.lower()]
    url = f"https://zh.wikisource.org/wiki/%E8%81%96%E7%B6%93_(%E6%96%87%E7%90%86%E5%92%8C%E5%90%88)/{chinese_book}"
    page = requests.get(url)
    soup = BeautifulSoup(page.content, "html.parser")


    def remove_digits(s):
        return ''.join([i for i in s if not i.isdigit()])


    passage = remove_digits(soup.find('span', {"id": verse}).parent.text).strip()
    return transliterate(passage) if translit else passage

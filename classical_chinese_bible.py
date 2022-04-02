from bs4 import BeautifulSoup
import requests

from bible_books_english_to_cc import english_to_cc
import transliteration.mandarin
import transliteration.middle_chinese
import transliteration.old_chinese


def remove_digits(s):
    return ''.join([i for i in s if not i.isdigit()])


def get_cc_verses(book, verses, translit=False, middle_chinese=False, old_chinese=False):
    print(f"Book: {book}, verses: {verses}")
    if "-" in verses:
        chapter = verses.split(":")[0].strip()
        verse_range = verses.split(":")[1]
        begin = int(verse_range.split("-")[0])
        end = int(verse_range.split("-")[1]) + 1
        passage = []
        for verse in range(begin, end):
            passage.append(get_cc_verse(book, chapter + ":" + str(verse), translit, middle_chinese, old_chinese))
        return "\n".join(passage)
    else:
        return get_cc_verse(book, verses, translit)


def get_cc_verse(book, verse, translit=False, middle_chinese=False, old_chinese=False):
    chinese_book = english_to_cc[book.lower()]
    url = f"https://zh.wikisource.org/wiki/%E8%81%96%E7%B6%93_(%E6%96%87%E7%90%86%E5%92%8C%E5%90%88)/{chinese_book}"
    page = requests.get(url)
    soup = BeautifulSoup(page.content, "html.parser")
    passage = remove_digits(soup.find('span', {"id": verse}).parent.text).strip()
    if translit:
        return transliteration.mandarin.transliterate(passage)
    if middle_chinese:
        return transliteration.middle_chinese.transliterate(passage)
    if old_chinese:
        return transliteration.old_chinese.transliterate(passage)
    return passage

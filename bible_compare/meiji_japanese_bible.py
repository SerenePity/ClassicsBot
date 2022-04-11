from bs4 import BeautifulSoup
import requests

from bible_compare.bible_books_english_to_japanese import english_to_japanese
import transliteration.transliteratable_versions


def get_meiji_japanese_verses(book, verses, translit=False):
    print(f"Getting Meiji verses, translit={translit}")
    if "-" in verses:
        chapter = verses.split(":")[0].strip()
        verse_range = verses.split(":")[1]
        begin = int(verse_range.split("-")[0])
        end = int(verse_range.split("-")[1]) + 1
        passage = []
        print(f"Book: {book}, Chapter: {chapter}, Begin: {begin}, End: {end}")
        for verse in range(begin, end):
            passage.append(get_meiji_japanese_verse(book, chapter + ":" + str(verse), translit))
        return "\n".join(passage)
    else:
        return get_meiji_japanese_verse(book, verses, translit)


def remove_digits(s):
    return ''.join([i for i in s if not i.isdigit()])


def get_meiji_japanese_verse(book, verse, translit=False):
    japanese_book = english_to_japanese[book.lower()]
    print(japanese_book)
    url = f"https://ja.wikisource.org/wiki/{japanese_book}"
    print(f"URL for Meiji: {url}")
    page = requests.get(url)
    soup = BeautifulSoup(page.content, "html.parser")
    passage = remove_digits(soup.find('span', {"id": verse}).parent.text).strip()
    if translit:
        passage = transliteration.transliteratable_versions.transliterate_verse("meiji", passage)
    return remove_digits(passage).strip()

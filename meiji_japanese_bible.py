from bs4 import BeautifulSoup
import requests

from bible_books_english_to_japanese import english_to_japanese


def get_meiji_japanese_verses(book, verses):
    if "-" in verses:
        chapter = verses.split(":")[0].strip()
        verse_range = verses.split(":")[1]
        begin = int(verse_range.split("-")[0])
        end = int(verse_range.split("-")[1]) + 1
        passage = []
        print(f"Book: {book}, Chapter: {chapter}, Begin: {begin}, End: {end}")
        for verse in range(begin, end):
            passage.append(get_meiji_japanese_verse(book, chapter + ":" + str(verse)))
        return "\n".join(passage)
    else:
        return get_meiji_japanese_verse(book, verses)


def remove_digits(s):
    return ''.join([i for i in s if not i.isdigit()])


def get_meiji_japanese_verse(book, verse):
    japanese_book = english_to_japanese[book.lower()]
    url = f"https://ja.wikisource.org/wiki/{japanese_book}"
    page = requests.get(url)
    soup = BeautifulSoup(page.content, "html.parser")
    passage = soup.find('span', {"id": verse}).parent.find_previous_sibling('p').text
    return remove_digits(passage).strip()

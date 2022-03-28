import requests
from bs4 import BeautifulSoup, Tag
from english_to_cc import english_to_cc


def get_cc_verses(book, verses):
    if "-" in verses:
        chapter = verses.split(" ")[1].split(":")[0].strip()
        verse_range = verses.split(":")[1]
        begin = int(verse_range.split("-")[0])
        end = int(verse_range.split("-")[1])
        for verse in range(begin, end):
            return get_cc_verse(book, chapter + ":" + verse)
    else:
        return get_cc_verse(book, verses)

def get_cc_verse(book, verse):
    chinese_book = english_to_cc[book]
    url = f"https://zh.wikisource.org/wiki/%E8%81%96%E7%B6%93_(%E6%96%87%E7%90%86%E5%92%8C%E5%90%88)/{chinese_book}"
    page = requests.get(url)
    soup = BeautifulSoup(page.content, "html.parser")

    def remove_digits(s):
        return ''.join([i for i in s if not i.isdigit()])
    passage = soup.find('span', {"id": verse}).parent.text

    return remove_digits(passage).strip()



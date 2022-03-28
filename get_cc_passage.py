import requests
from bs4 import BeautifulSoup, Tag
from english_to_cc import english_to_cc

def get_cc_verse(id, book):
    chinese_book = english_to_cc[book]

    url = f"https://zh.wikisource.org/wiki/%E8%81%96%E7%B6%93_(%E6%96%87%E7%90%86%E5%92%8C%E5%90%88)/{chinese_book}"
    page = requests.get(url)
    soup = BeautifulSoup(page.content, "html.parser")

    def remove_digits(s):
        return ''.join([i for i in s if not i.isdigit()])
    return remove_digits(soup.find('span', {"id": id}).parent.text).strip()




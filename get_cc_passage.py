import requests
from bs4 import BeautifulSoup, Tag
from english_to_cc import english_to_cc

chinese = english_to_cc["Genesis"]
def get_cc_verse():

    url = f"https://zh.wikisource.org/wiki/%E8%81%96%E7%B6%93_(%E6%96%87%E7%90%86%E5%92%8C%E5%90%88)/{chinese}"
    page = requests.get(url)
    soup = BeautifulSoup(page.content, "html.parser")

    def remove_digits(s):
        return ''.join([i for i in s if not i.isdigit()])
    passage = soup.find('span', {"id": "1:1"}).parent


print(get_cc_verse())




import random

import requests
from bs4 import BeautifulSoup
from dynaconf import settings
from requests import HTTPError


def _ru_ru_get_joke():
    try:
        res = requests.get(settings.JOKE_SOURCE["ru_RU"])
        res.encoding = 'utf-8'
        res.raise_for_status()
        soup = BeautifulSoup(res.content)
        lst = soup.select(".text[id]")
        item = random.choice(lst)
        return item.text
    except HTTPError:
        return None


def get_joke(lang):
    if lang == "ru_RU":
        return _ru_ru_get_joke()

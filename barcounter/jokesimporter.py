import random

import requests
from bs4 import BeautifulSoup, ParserRejectedMarkup
from dynaconf import settings
from requests import HTTPError

from barcounter import log

logger = log


def _ru_ru_get_joke():
    try:
        res = requests.get(settings.JOKE_SOURCE["ru_RU"])
        res.encoding = 'utf-8'
        res.raise_for_status()
        soup = BeautifulSoup(res.content, features="html.parser")
        lst = soup.select(".text[id]")
        item = random.choice(lst)
        return item.text
    except HTTPError or ParserRejectedMarkup or IndexError as e:
        logger.error(str(e))
        return None


def get_joke(lang):
    if lang == "ru_RU":
        return _ru_ru_get_joke()

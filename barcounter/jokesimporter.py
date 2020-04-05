import random

import requests
from bs4 import BeautifulSoup, ParserRejectedMarkup
from dynaconf import settings
from requests import HTTPError

from barcounter import log

logger = log


def _ru_ru_get_joke():
    try:
        package = settings.JOKE_SOURCE["ru_RU"]
        url = package.url
        name = package.name
        res = requests.get(url)
        res.encoding = 'utf-8'
        res.raise_for_status()
        soup = BeautifulSoup(res.content, features="html.parser")
        lst = soup.select(".text[id]")
        item = random.choice(lst)
        out = ""
        for content in item.contents:
            if content.name == "br":
                out += '\n'
            else:
                out += str(content)
        return out + "\n(c) " + name
    except HTTPError or ParserRejectedMarkup or IndexError as e:
        logger.error(str(e))
        return None


def get_joke(lang):
    if lang == "ru_RU":
        return _ru_ru_get_joke()

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
    except (HTTPError, ParserRejectedMarkup, IndexError) as e:
        logger.error(str(e))
        return None


def _en_us_get_joke():
    try:
        package = settings.JOKE_SOURCE["en_US"]
        res = requests.get(package.url)
        res.encoding = 'utf-8'
        res.raise_for_status()
        json_res = a.json()
        joke_setup = json_res.get('setup', None)
        joke_punchline = json_res.get('punchline', None)
        assert joke_setup is not None
        assert joke_punchline is not None
        return "{setup} {punchline}".format(setup=joke_setup, punchline=joke_punchline)
    except (HTTPError, AssertionError) as e:
        logger.error(str(e))
        return None


def get_joke(lang):
    if lang == "ru_RU":
        return _ru_ru_get_joke()
    elif lang == "en_US":
        return _en_us_get_joke()

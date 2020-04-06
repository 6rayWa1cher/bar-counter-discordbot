import random
from collections import Iterable

from dynaconf import settings


def lang_raw(lang_code, *path):
    package = settings.LANG[lang_code]
    for p in path:
        package = package[p]
    return package


def lang(lang_code, *path, fail_to_en_us=True):
    package = settings.LANG[lang_code]
    for p in path:
        if p not in package and lang_code != "en_US" and fail_to_en_us:
            return lang("en_US", *path)
        package = package[p]
    if isinstance(package, Iterable) and not isinstance(package, str):
        return random.choice(list(package))
    else:
        return package


def get_langs():
    package = settings.LANG
    return package.keys()


def international(name):
    return settings.INTERNATIONAL[name]


def limitation(name):
    return settings.LIMITATIONS[name]

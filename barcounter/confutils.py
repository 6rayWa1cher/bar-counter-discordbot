import random
from collections import Iterable

from dynaconf import settings


def lang(lang_code, *path):
    package = settings.LANG[lang_code]
    for p in path:
        package = package[p]
    if isinstance(package, Iterable) and not isinstance(package, str):
        return random.choice(list(package))
    else:
        return package


def limitation(name):
    return settings.LIMITATIONS[name]

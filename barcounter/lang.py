from random import random

from dynaconf import settings


def get_string(lang, *path):
    package = settings.LANG[lang]
    for p in path:
        package = package[p]
    if package is list:
        return random.choice(package)
    else:
        return package

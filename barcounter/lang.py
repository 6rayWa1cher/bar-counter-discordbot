from dynaconf import settings


def get_string(lang, *path):
    package = settings.LANG[lang]
    for p in path:
        package = package[p]
    return package

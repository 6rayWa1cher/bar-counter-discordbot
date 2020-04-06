from typing import Optional

from discord import Guild
from discord.ext.commands import Context

from barcounter import confutils as conf, db, log
from barcounter.dbentities import Server, Person, Drink


def get_server_or_create(gid: int, preferred_locale: Optional[str]) -> Server:
    preferred_locale = preferred_locale.replace("-", "_")
    if preferred_locale is not None and preferred_locale in conf.get_langs():
        return Server.get_or_create(sid=gid, defaults={"lang": preferred_locale})[0]
    else:
        return Server.get_or_create(sid=gid, defaults={"lang": "en_US"})[0]


def get_server_from_context(ctx: Context) -> Server:
    return get_server_or_create(ctx.guild.id, ctx.guild.preferred_locale)


def get_lang(gid: int, preferred_locale: Optional[str]):
    return get_server_or_create(gid, preferred_locale).lang


def get_lang_from_context(ctx: Context):
    return get_lang(ctx.guild.id, ctx.guild.preferred_locale)


def get_lang_from_guild(guild: Guild):
    return get_lang(guild.id, guild.preferred_locale)


def get_person_or_create(gid: int, uid: int, preferred_locale: Optional[str]):
    server = get_server_or_create(gid, preferred_locale)
    return Person.get_or_create(server=server, uid=uid, defaults={"intoxication": 0})[0]


async def add_default_drinks(guild):
    server = get_server_or_create(guild.id, guild.preferred_locale)
    default_drinks = conf.lang_raw(server.lang, "default_drinks")
    with db.atomic():
        for default_drink in default_drinks:
            Drink.create(server=server, name=default_drink.name, intoxication=default_drink.intoxication,
                         portion_size=default_drink.portion, portions_per_day=default_drink.portions_per_day,
                         portions_left=default_drink.portions_per_day)
    log.info("Added drinks to {0}".format(guild.id))

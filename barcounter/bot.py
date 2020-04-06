import asyncio
import logging
import os
import sys
from logging.handlers import RotatingFileHandler

from discord.ext import commands
from dynaconf import settings


def setup_logger():
    logger = logging.getLogger('discord')
    logger.setLevel(logging.INFO)
    handler = RotatingFileHandler(filename=os.path.join(settings["LOGS_LOCATION"], 'discord.log'), encoding='utf-8',
                                  mode='w', maxBytes=8 * 1024 * 1024)
    handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
    logger.addHandler(handler)

    logger = logging.getLogger('barcounter')
    logger.setLevel(logging.INFO)
    handler1 = RotatingFileHandler(filename=os.path.join(settings["LOGS_LOCATION"], 'barcounter.log'), encoding='utf-8',
                                   mode='w', maxBytes=8 * 1024 * 1024)
    handler1.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
    handler2 = logging.StreamHandler(stream=sys.stdout)
    handler2.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
    logger.addHandler(handler1)
    logger.addHandler(handler2)


def start():
    setup_logger()
    token = settings.TOKEN
    bot = commands.Bot(command_prefix=settings.COMMAND_PREFIX)
    bot.load_extension("barcounter.cogs.drinkcog")
    bot.load_extension("barcounter.cogs.roleregistrarcog")
    bot.load_extension("barcounter.cogs.settingscog")
    logging.getLogger('barcounter').info("Connecting...")
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(bot.start(token))
    except KeyboardInterrupt:
        loop.run_until_complete(bot.logout())
        # cancel all tasks lingering
    finally:
        loop.close()

import logging

from . import bot

bot.setup_logger()
log = logging.getLogger('barcounter')

from barcounter.cogs import drinkcog

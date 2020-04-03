import logging

from peewee import SqliteDatabase

from barcounter.cogs import *
from . import bot

bot.setup_logger()
log = logging.getLogger('barcounter')
db = SqliteDatabase('sqlite.db')

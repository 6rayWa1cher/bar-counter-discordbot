import logging

from dynaconf import settings
from peewee import SqliteDatabase

db = SqliteDatabase(settings["DB_LOCATION"], autoconnect=True,
                    autocommit=True)

from barcounter.cogs import *
from . import bot

log = logging.getLogger('barcounter')

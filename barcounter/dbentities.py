from peewee import *

from barcounter import confutils as conf
from . import db

DRINK_NAME_LENGTH = conf.limitation("drink_name_length")


class AbstractModel(Model):
    class Meta:
        database = db


class Server(AbstractModel):
    sid = IntegerField()
    lang = CharField()


class Person(AbstractModel):
    uid = IntegerField()
    server = ForeignKeyField(Server, backref="persons")
    intoxication = IntegerField()


class Drink(AbstractModel):
    server = ForeignKeyField(Server, backref="drinks")
    name = CharField(max_length=DRINK_NAME_LENGTH)
    intoxication = IntegerField()
    portion_size = IntegerField()
    portions_per_day = IntegerField()
    portions_left = IntegerField()

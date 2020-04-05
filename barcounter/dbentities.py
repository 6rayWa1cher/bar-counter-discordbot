from peewee import *

from barcounter import confutils as conf
from . import db

DRINK_NAME_LENGTH = conf.limitation("drink_name_length")


class AbstractModel(Model):
    class Meta:
        database = db


class Person(AbstractModel):
    uid = IntegerField()
    server = IntegerField()
    intoxication = IntegerField()


class Drink(AbstractModel):
    server = IntegerField()
    name = CharField(max_length=DRINK_NAME_LENGTH)
    intoxication = IntegerField()
    portion_size = IntegerField()
    portions_per_day = IntegerField()
    portions_left = IntegerField()

from peewee import *

from . import db


class AbstractModel(Model):
    class Meta:
        database = db


class Person(AbstractModel):
    id = IntegerField()
    server = IntegerField()
    intoxication = IntegerField()


class Drink(AbstractModel):
    server = IntegerField()
    name = CharField()
    intoxication = IntegerField()
    portion_size = IntegerField()
    portions_per_day = IntegerField()
    portions_left = IntegerField()

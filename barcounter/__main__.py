from . import bot, dbentities, db

with db:
    db.create_tables([dbentities.Drink, dbentities.Person])

bot.start()

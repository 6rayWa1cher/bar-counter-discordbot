from . import bot, dbentities, db

db.connect()
db.create_tables([dbentities.Drink])

bot.start()

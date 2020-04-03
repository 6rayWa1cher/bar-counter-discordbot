from discord import Guild, Member, Forbidden
from discord.ext import commands
from discord.ext.commands import Context

from barcounter import lang, log
from barcounter.dbentities import Drink, Person
from barcounter.jokesimporter import get_joke

logger = log


async def consume_drink(ctx: Context, person: Person, drink: Drink):
    if person.intoxication > 100 or person.intoxication < 0:
        person.intoxication = 0
    guild: Guild = ctx.guild
    member: Member = guild.get_member(person.id)

    if drink.portions_left <= 0:
        await ctx.send(lang.get_string("ru_RU", "no_portions_left").format(drink.name))
    else:
        if drink.portions_left == 1:
            await ctx.send(lang.get_string("ru_RU", "last_portion").format(drink.name))
        person.intoxication += drink.intoxication
        drink.portions_left -= 1
        if person.intoxication >= 100:
            try:
                await member.move_to(None, reason="Drank too much")
                await ctx.send(lang.get_string("ru_RU", "overdrink_kick_message").format(member.mention))
            except Forbidden:
                log.info("Can't kick an alcoholic: no permissions in " + guild.id)
                await ctx.send(lang.get_string("ru_RU", "overdrink_no_kick_message").format(member.mention))
            finally:
                person.intoxication = 0
        elif person.intoxication > 80:
            await ctx.send(lang.get_string("ru_RU", "pre_overdrink"))
    person.save()
    drink.save()


class DrinkCog(commands.Cog):
    """
    Commands to give you a virtual drink
    """

    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def list(self, ctx: Context):
        """
        Returns the list with available drinks
        """
        drinks = lang.get_string("ru_RU", "default_drinks")
        out = ""
        for drink in drinks:
            out += lang.get_string("ru_RU", "drink_info").format(str(drink.name), str(drink.portion))
        await ctx.send(out)

    @commands.command()
    async def drink(self, ctx: Context, *, to_drink: str):
        """
        Drinks a drink and tails some random joke
        """
        async with ctx.typing():
            joke = get_joke("ru_RU")
        await ctx.send(joke)

    @commands.command()
    @commands.has_role("barman")
    async def add_drink(self, ctx: Context, *, drink_name: str, intoxication: int = 20, portion_size: int = 200,
                        portions_per_day: int = 10):
        if not 0 <= intoxication <= 100:
            await ctx.send(lang.get_string("ru_RU", "wrong_intoxication"))
            return
        if not 0 < portion_size:
            await ctx.send(lang.get_string("ru_RU", "wrong_portion_size"))
            return
        if not 0 < portions_per_day:
            await ctx.send(lang.get_string("ru_RU", "wrong_portions_per_day"))
            return
        drink: Drink = Drink(server=ctx.guild.id, name=drink_name, intoxication=intoxication, portion_size=portion_size,
                             portions_per_day=portions_per_day, portions_left=portions_per_day)
        drink.save()
        await ctx.send(lang.get_string("ru_RU", "drink_added"))


def setup(bot):
    bot.add_cog(DrinkCog(bot))

from discord.ext import commands

from .. import lang
from .. import log
from ..jokesimporter import get_joke

logger = log


class DrinkCog(commands.Cog):
    """
    Commands to give you a virtual drink
    """

    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def list(self, ctx: commands.context.Context):
        """
        Returns the list with available drinks
        """
        drinks = lang.get_string("ru_RU", "default_drinks")
        out = ""
        for drink in drinks:
            out += lang.get_string("ru_RU", "drink_info").format(drink.name, drink.portion)
        await ctx.send(out)

    @commands.command()
    async def drink(self, ctx: commands.context.Context, *, to_drink: str):
        """
        Drinks a drink and tails some random joke
        """
        with ctx.typing():
            joke = get_joke("ru_RU")
        await ctx.send(joke)


def setup(bot):
    bot.add_cog(DrinkCog(bot))

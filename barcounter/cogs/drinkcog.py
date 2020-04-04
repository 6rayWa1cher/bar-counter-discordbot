import asyncio
from datetime import datetime, timedelta
from typing import Optional

from discord import Guild, Member, Forbidden, NotFound, HTTPException
from discord.ext import commands, tasks
from discord.ext.commands import Context

from barcounter import confutils as conf, log, db
from barcounter.dbentities import Drink, Person, DoesNotExist
from barcounter.jokesimporter import get_joke

logger = log

DRINKS_PER_SERVER = conf.limitation("drinks_per_server")
DRINK_NAME_LENGTH = conf.limitation("drink_name_length")
PORTIONS_PER_DAY = conf.limitation("portions_per_day")
PORTION_MAX_SIZE = conf.limitation("portion_max_size")
DEFAULT_INTOXICATION = 20
DEFAULT_PORTION_SIZE = 100
DEFAULT_PORTIONS_PER_DAY = 10


async def consume_drink(ctx: Context, person: Person, drink: Drink):
    if person.intoxication > 100 or person.intoxication < 0:
        person.intoxication = 0
    guild: Guild = ctx.guild
    member: Member = guild.get_member(person.id)

    if drink.portions_left <= 0:
        await ctx.send(conf.lang("ru_RU", "no_portions_left").format(drink.name))
    else:
        if drink.portions_left == 1:
            await ctx.send(conf.lang("ru_RU", "last_portion").format(drink.name))
        person.intoxication += drink.intoxication
        drink.portions_left -= 1
        if person.intoxication >= 100:
            try:
                await member.move_to(None, reason="Drank too much")
                await ctx.send(conf.lang("ru_RU", "overdrink_kick_message").format(member.mention))
            except Forbidden:
                log.info("Can't kick an alcoholic: no permissions in " + guild.id)
                await ctx.send(conf.lang("ru_RU", "overdrink_no_kick_message").format(member.mention))
            finally:
                person.intoxication = 0
        elif person.intoxication > 80:
            await ctx.send(conf.lang("ru_RU", "pre_overdrink").format(member.display_name))
        log.info("{0} consumed drink \"{1}\" on {2}".format(member.display_name, drink.name, guild.id))
    with db.atomic():
        person.save()
        drink.save()


def get_person_or_create(gid: int, uid: int):
    return Person.get_or_create(server=gid, id=uid, defaults={"intoxication": 0})[0]


def check_guild_drink_count(gid: int):
    return Drink.select().where(Drink.server == gid).count() < DRINKS_PER_SERVER


class DrinkCog(commands.Cog):
    """
    Commands to give you a virtual drink
    """

    def __init__(self, bot):
        self.bot = bot
        self.message_dict = dict()

    @commands.Cog.listener()
    async def on_ready(self):
        log.info("Successfully connected and ready")

    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        log.info("Joined guild {0}".format(guild.id))
        default_drinks = conf.lang("ru_RU", "default_drinks")
        with db.atomic():
            for default_drink in default_drinks:
                Drink.create(server=guild.id, name=default_drink.name, intoxication=default_drink.intoxication,
                             portion_size=default_drink.portion, portions_per_day=default_drink.portions_per_day,
                             portions_left=default_drink.portions_per_day)
        log.info("Added drinks to {0}".format(guild.id))
        return True

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        log.debug("Got reaction {0} by {1} on {2}".format(str(reaction), user, str(reaction.message.guild)))
        message = reaction.message
        mid = message.id
        if mid not in self.message_dict:
            return
        ctx, _, expected, _, drink = self.message_dict[mid]
        if user != expected or message.id not in self.message_dict:
            return
        if str(reaction) == conf.lang("ru_RU", "ok-emoji"):
            log.debug("Parsed as OK")
            await self.drink(ctx, drink.name)
            try:
                await message.delete()
            except Forbidden or NotFound or HTTPException:
                pass
            finally:
                del self.message_dict[message.id]
        elif str(reaction) == conf.lang("ru_RU", "no-emoji"):
            log.debug("Parsed as NO")
            try:
                await message.delete()
            except Forbidden or NotFound or HTTPException:
                pass
            finally:
                del self.message_dict[message.id]

    @tasks.loop(minutes=10)
    async def erase(self):
        now = datetime.today()
        for mid, tpl in self.message_dict.items():
            ctx, message, user, time, drink = tpl
            if now > time:
                try:
                    await message.delete()
                except Forbidden or NotFound or HTTPException:
                    pass
                finally:
                    del self.message_dict[mid]
                    log.info("Deleted message {0} on {1} by time exceeding".format(message.id, ctx.guild.id))

    @commands.command()
    @commands.guild_only()
    async def list(self, ctx: Context):
        """
        Returns the list with available drinks
        """
        drinks = Drink.select().where(Drink.server == ctx.guild.id)
        out = ""
        for drink in drinks:
            out += conf.lang("ru_RU", "drink_info").format(str(drink.name), str(drink.portion_size))
            out += '\n'
        await ctx.send(out)

    @commands.command()
    @commands.guild_only()
    @commands.bot_has_permissions(move_members=True)
    async def drink(self, ctx: Context, drink_name: str):
        """
        Drinks a drink and tails some random joke.

        Parameters:
        drink_name: name of the drink, not empty
        """
        if ctx.invoked_subcommand is not None:
            return
        if drink_name is None or len(drink_name) > DRINK_NAME_LENGTH:
            await ctx.send(conf.lang("ru_RU", "wrong_drink_name").format(DRINK_NAME_LENGTH))
            return
        try:
            drink = Drink.get(Drink.server == ctx.guild.id and Drink.name == drink_name)
            person = get_person_or_create(ctx.guild.id, ctx.author.id)
            await consume_drink(ctx, person, drink)
            async with ctx.typing():
                joke = get_joke("ru_RU")
            await ctx.send(joke or conf.lang("ru_RU", "joke_not_loaded"))
        except DoesNotExist:
            await ctx.send(conf.lang("ru_RU", "drink_not_found").format(drink_name))

    @commands.command()
    @commands.has_role("barman")
    @commands.guild_only()
    async def add(self, ctx: Context, drink_name: str, intoxication: int = DEFAULT_INTOXICATION,
                  portion_size: int = DEFAULT_PORTION_SIZE,
                  portions_per_day: int = DEFAULT_PORTIONS_PER_DAY):
        """
        Add a new drink to the bar. Barman role required.

        Parameters:
        drink_name: name of the drink, not empty
        intoxication: percent of intoxication (0-100). When man drinks a drink, this value will
        be appended to the level of intoxication.
        portion_size: size of portion, in milliliters, greater than 0 and less than 10000 (10l).
        portions_per_day: portions of this drink available for one day, greater than 0 and less
        than 10000.
        """
        if not 0 <= intoxication <= 100:
            await ctx.send(conf.lang("ru_RU", "wrong_intoxication"))
        elif not 0 < portion_size <= PORTION_MAX_SIZE:
            await ctx.send(conf.lang("ru_RU", "wrong_portion_size").format(PORTION_MAX_SIZE))
        elif not 0 < portions_per_day <= PORTIONS_PER_DAY:
            await ctx.send(conf.lang("ru_RU", "wrong_portions_per_day").format(PORTIONS_PER_DAY))
        elif drink_name is None or len(drink_name) > DRINK_NAME_LENGTH:
            await ctx.send(conf.lang("ru_RU", "wrong_drink_name").format(DRINK_NAME_LENGTH))
        elif not check_guild_drink_count(ctx.guild.id):
            await ctx.send(conf.lang("ru_RU", "too_many_drinks").format(DRINKS_PER_SERVER))
        else:
            Drink.create(server=ctx.guild.id, name=drink_name, intoxication=intoxication,
                         portion_size=portion_size,
                         portions_per_day=portions_per_day, portions_left=portions_per_day)
            await ctx.send(conf.lang("ru_RU", "drink_added").format(drink_name))
            log.info("Added drink \"{0}\" on {1}".format(drink_name, ctx.guild.id))

    @commands.command()
    @commands.has_role("barman")
    @commands.guild_only()
    async def remove(self, ctx: Context, *, drink_name: str):
        """
        Remove the drink from the bar. Barman role required.

        Parameters:
        drink_name: name of the drink, not empty
        """
        if drink_name in None or len(drink_name) > DRINK_NAME_LENGTH:
            await ctx.send(conf.lang("ru_RU", "wrong_drink_name").format(DRINK_NAME_LENGTH))
            return
        try:
            drink = Drink.get(Drink.server == ctx.guild.id and Drink.name == drink_name)
            drink.delete_instance()
            await ctx.send(conf.lang("ru_RU", "drink_deleted"))
            log.info("Removed drink \"{0}\" from {1}".format(drink_name, ctx.guild.id))
        except DoesNotExist:
            await ctx.send(conf.lang("ru_RU", "drink_not_found").format(drink_name))

    @commands.command()
    @commands.has_role("barman")
    @commands.guild_only()
    async def restock(self, ctx: Context, *, drink_name: Optional[str]):
        """
        Restock the bar or only one drink. Barman role required.

        Parameters:
        drink_name: name of the drink
        """
        if drink_name is not None and len(drink_name) > DRINK_NAME_LENGTH:
            await ctx.send(conf.lang("ru_RU", "wrong_drink_name").format(DRINK_NAME_LENGTH))
            return
        if drink_name is None:
            (Drink.update(portions_left=Drink.portions_per_day)
             .where(Drink.server == ctx.guild.id)
             ).execute()
            await ctx.send(conf.lang("ru_RU", "restocked_all"))
            log.info("Restocked all drinks on {1}".format(drink_name, ctx.guild.id))
        else:
            (Drink.update(portions_left=Drink.portions_per_day)
             .where(Drink.server == ctx.guild.id and Drink.server == drink_name)
             ).execute()
            await ctx.send(conf.lang("ru_RU", "restocked_single").format(drink_name))
            log.info("Restocked drink \"{0}\" on {1}".format(drink_name, ctx.guild.id))

    @commands.command()
    @commands.guild_only()
    @commands.bot_has_permissions(add_reactions=True, send_messages=True, move_members=True)
    async def serve(self, ctx: Context, drink_name: str, to: Member):
        """
        Trying to give a drink to the member.

        This command will send a message, where the member can choose to drink or not.
        Parameters:
        drink_name: name of the drink
        to: member (can be mention)
        """
        gid = ctx.guild.id
        try:
            drink = Drink.get(Drink.server == gid and Drink.name == drink_name)
        except DoesNotExist:
            if not check_guild_drink_count(gid):
                await ctx.send(conf.lang("ru_RU", "too_many_drinks").format(DRINKS_PER_SERVER))
                return
            drink = Drink.create(server=gid, name=drink_name, intoxication=DEFAULT_INTOXICATION,
                                 portion_size=DEFAULT_PORTION_SIZE,
                                 portions_per_day=DEFAULT_PORTIONS_PER_DAY,
                                 portions_left=DEFAULT_PORTIONS_PER_DAY)
        msg = await ctx.send(
            conf.lang("ru_RU", "serve_message").format(author=ctx.author.mention, drink=drink_name,
                                                       portion_size=drink.portion_size))

        await asyncio.wait(
            {msg.add_reaction(conf.lang("ru_RU", "ok-emoji")), msg.add_reaction(conf.lang("ru_RU", "no-emoji"))})
        self.message_dict[msg.id] = (ctx, msg, to, datetime.today() + timedelta(0, 60 * 10), drink)

    @commands.command()
    @commands.has_role("barman")
    @commands.guild_only()
    async def reset(self, ctx: Context):
        """
        Reset all drinks to defaults. Barman role required.
        """
        Drink.delete().where(Drink.server == ctx.guild.id).execute()
        await self.on_guild_join(ctx.guild)


def setup(bot):
    bot.add_cog(DrinkCog(bot))

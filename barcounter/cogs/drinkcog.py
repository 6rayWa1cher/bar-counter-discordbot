import asyncio

import aiocron as aiocron
from discord import Member, Forbidden
from discord.ext import commands
from discord.ext.commands import Bot

from barcounter.cogs.helpers import *
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


async def consume_drink(ctx: Context, person: Person, drink: Drink, member: Member):
    if person.intoxication > 100 or person.intoxication < 0:
        person.intoxication = 0
    guild: Guild = ctx.guild
    # member: Member = guild.get_member(person.uid)
    lang = get_lang_from_context(ctx)

    if drink.portions_left <= 0:
        await ctx.send(conf.lang(lang, "no_portions_left").format(drink.name))
    else:
        if drink.portions_left == 1:
            await ctx.send(conf.lang(lang, "last_portion").format(drink.name))
        person.intoxication += drink.intoxication
        drink.portions_left -= 1
        if person.intoxication >= 100:
            try:
                await member.move_to(None, reason="Drank too much")
                await ctx.send(conf.lang(lang, "overdrink_kick_message").format(member.mention))
            except Forbidden:
                log.info("Can't kick an alcoholic: no permissions in " + guild.id)
                await ctx.send(conf.lang(lang, "overdrink_no_kick_message").format(member.mention))
            finally:
                person.intoxication = 0
        elif person.intoxication > 80:
            await ctx.send(conf.lang(lang, "pre_overdrink").format(member.display_name))
        log.info("{0} consumed drink \"{1}\" on {2}".format(member.display_name, drink.name, guild.id))
    with db.atomic():
        person.save()
        drink.save()


def check_guild_drink_count(gid: int):
    return Drink.select(Drink).join(Server).where(Server.sid == gid).count() < DRINKS_PER_SERVER


@aiocron.crontab("0 0 * * *")
async def restock():
    (Drink.update(portions_left=Drink.portions_per_day)).execute()
    log.info("Restocked every server")


@aiocron.crontab("* * * * *")
async def deintoxication():
    delta = 1
    (Person.update(intoxication=Person.intoxication - delta).where(Person.intoxication >= delta)).execute()
    (Person.update(intoxication=0).where(Person.intoxication < delta)).execute()


async def give_a_drink(ctx, member, drink):
    lang = get_lang_from_context(ctx)
    person = get_person_or_create(ctx.guild.id, member.id, ctx.guild.preferred_locale)
    await consume_drink(ctx, person, drink, member)
    async with ctx.typing():
        joke = get_joke(lang)
    await ctx.send(joke or conf.lang(lang, "joke_not_loaded"))


def not_barman(coro):
    async def process(self, ctx, error):
        if isinstance(error, commands.MissingRole) and error.missing_role == "barman":
            await ctx.send(get_lang_from_context(ctx), "missing_role")
        else:
            await coro(self, ctx, error)

    return process


class DrinkCog(commands.Cog):
    """
    Commands to give you a virtual drink
    """

    def __init__(self, bot):
        self.bot: Bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        log.info("Successfully connected and ready")

    @commands.Cog.listener()
    async def on_guild_join(self, guild: Guild):
        log.info("Joined guild {0}".format(guild.id))
        await add_default_drinks(guild)
        server = get_server_or_create(guild.id, guild.preferred_locale)
        if guild.system_channel is not None:
            await guild.system_channel.send(
                conf.lang(server.lang, "greetings").format(self.bot.user.name, self.bot.command_prefix,
                                                           conf.international("greetings_ending").format(
                                                               self.bot.command_prefix)))
        return True

    @commands.Cog.listener()
    async def on_guild_remove(self, guild):
        log.info("Removing guild {0}".format(guild.id))
        server = get_server_or_create(guild.id, guild.preferred_locale)
        with db.atomic():
            Drink.delete().where(Drink.server == server).execute()
            Person.delete().where(Person.server == server).execute()
            server.delete_instance()
        return True

    @commands.command()
    @commands.guild_only()
    async def list(self, ctx: Context):
        """
        Returns the list with available drinks
        """
        server = get_server_from_context(ctx)
        lang = server.lang
        drinks = Drink.select().where(Drink.server == server)
        out = "\n".join([
            conf.lang(lang, "drink_info").format(drink.name, drink.portion_size, drink.portions_left,
                                                 drink.portions_per_day)
            for drink in drinks
        ])
        if out != "":
            await ctx.send(out)
        else:
            await ctx.send(conf.lang(lang, "no_drinks"))

    @commands.command()
    @commands.guild_only()
    @commands.bot_has_guild_permissions(move_members=True)
    async def drink(self, ctx: Context, *, drink_name: str):
        """
        Drinks a drink and tails some random joke.

        Parameters:
        drink_name: name of the drink, not empty
        """
        server = get_server_from_context(ctx)
        lang = server.lang
        if drink_name is None or len(drink_name) > DRINK_NAME_LENGTH:
            await ctx.send(conf.lang(lang, "wrong_drink_name").format(DRINK_NAME_LENGTH))
            return
        try:
            drink = Drink.get(Drink.server == server and Drink.name == drink_name)
        except DoesNotExist:
            await ctx.send(conf.lang(lang, "drink_not_found").format(drink_name))
        else:
            await give_a_drink(ctx, ctx.author, drink)

    @drink.error
    async def drink_error(self, ctx, error):
        if isinstance(error, commands.BotMissingPermissions):
            await ctx.send(conf.lang(get_lang_from_context(ctx), "missing_permissions", "drink"))
            error.bcdb_checked = True

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
        server = get_server_from_context(ctx)
        lang = server.lang
        if not 0 <= intoxication <= 100:
            await ctx.send(conf.lang(lang, "wrong_intoxication"))
        elif not 0 < portion_size <= PORTION_MAX_SIZE:
            await ctx.send(conf.lang(lang, "wrong_portion_size").format(PORTION_MAX_SIZE))
        elif not 0 < portions_per_day <= PORTIONS_PER_DAY:
            await ctx.send(conf.lang(lang, "wrong_portions_per_day").format(PORTIONS_PER_DAY))
        elif drink_name is None or len(drink_name) > DRINK_NAME_LENGTH:
            await ctx.send(conf.lang(lang, "wrong_drink_name").format(DRINK_NAME_LENGTH))
        elif not check_guild_drink_count(ctx.guild.id):
            await ctx.send(conf.lang(lang, "too_many_drinks").format(DRINKS_PER_SERVER))
        elif Drink.select().where(Drink.server == ctx.guild.id and Drink.name == drink_name).count() > 0:
            await ctx.send(conf.lang(lang, "duplicate_drink").format(drink_name))
        else:
            Drink.create(server=server, name=drink_name, intoxication=intoxication,
                         portion_size=portion_size,
                         portions_per_day=portions_per_day, portions_left=portions_per_day)
            await ctx.send(conf.lang(lang, "drink_added").format(drink_name))
            log.info("Added drink \"{0}\" on {1}".format(drink_name, ctx.guild.id))

    @add.error
    @not_barman
    def add_error(self, ctx, error):
        pass

    @commands.command()
    @commands.has_role("barman")
    @commands.guild_only()
    async def remove(self, ctx: Context, *, drink_name: str):
        """
        Remove the drink from the bar. Barman role required.

        Parameters:
        drink_name: name of the drink, not empty
        """
        server = get_server_from_context(ctx)
        lang = server.lang
        if drink_name is None or len(drink_name) > DRINK_NAME_LENGTH:
            await ctx.send(conf.lang(lang, "wrong_drink_name").format(DRINK_NAME_LENGTH))
            return
        try:
            drink = Drink.get(Drink.server == server and Drink.name == drink_name)
            drink.delete_instance()
            await ctx.send(conf.lang(lang, "drink_deleted").format(drink_name))
            log.info("Removed drink \"{0}\" from {1}".format(drink_name, ctx.guild.id))
        except DoesNotExist:
            await ctx.send(conf.lang(lang, "drink_not_found").format(drink_name))

    @remove.error
    @not_barman
    def remove_error(self, ctx, error):
        pass

    @commands.command()
    @commands.has_role("barman")
    @commands.guild_only()
    async def restock(self, ctx: Context, *, drink_name: Optional[str]):
        """
        Restock the bar or only one drink. Barman role required.

        Parameters:
        drink_name: name of the drink
        """
        server = get_server_from_context(ctx)
        lang = server.lang
        if drink_name is not None and len(drink_name) > DRINK_NAME_LENGTH:
            await ctx.send(conf.lang(lang, "wrong_drink_name").format(DRINK_NAME_LENGTH))
            return
        if drink_name is None:
            (Drink.update(portions_left=Drink.portions_per_day)
             .where(Drink.server == server)
             ).execute()
            await ctx.send(conf.lang(lang, "restocked_all"))
            log.info("Restocked all drinks on {1}".format(drink_name, ctx.guild.id))
        else:
            (Drink.update(portions_left=Drink.portions_per_day)
             .where(Drink.server == server and Drink.name == drink_name)
             ).execute()
            await ctx.send(conf.lang(lang, "restocked_single").format(drink_name))
            log.info("Restocked drink \"{0}\" on {1}".format(drink_name, ctx.guild.id))

    @restock.error
    @not_barman
    def restock_error(self, ctx, error):
        pass

    @commands.command()
    @commands.guild_only()
    @commands.bot_has_guild_permissions(add_reactions=True, move_members=True)
    async def serve(self, ctx: Context, drink_name: str, to: commands.Greedy[Member]):
        """
        Trying to give a drink to the member.

        This command will send a message, where the member can choose to drink or not.
        Parameters:
        drink_name: name of the drink
        to: member (can be mention)
        """
        gid = ctx.guild.id
        server = get_server_from_context(ctx)
        lang = server.lang
        try:
            drink = Drink.get(Drink.server == server and Drink.name == drink_name)
        except DoesNotExist:
            if not check_guild_drink_count(gid):
                await ctx.send(conf.lang(lang, "too_many_drinks").format(DRINKS_PER_SERVER))
                return
            drink = Drink.create(server=server, name=drink_name, intoxication=DEFAULT_INTOXICATION,
                                 portion_size=DEFAULT_PORTION_SIZE,
                                 portions_per_day=DEFAULT_PORTIONS_PER_DAY,
                                 portions_left=DEFAULT_PORTIONS_PER_DAY)
        msg = await ctx.send(
            conf.lang(lang, "serve_message").format(author=ctx.author.mention, drink=drink_name,
                                                    portion_size=drink.portion_size))

        await msg.add_reaction(conf.lang(lang, "ok-emoji"))
        await msg.add_reaction(conf.lang(lang, "no-emoji"))
        expected = set(to)

        def check(reaction, user):
            return user in expected and str(reaction.emoji) in {conf.lang(lang, "ok-emoji"),
                                                                conf.lang(lang, "no-emoji")}

        while len(expected):
            try:
                reaction, user = await self.bot.wait_for("reaction_add", timeout=conf.limitation("serve_timeout"),
                                                         check=check)
            except asyncio.TimeoutError:
                break
            else:
                expected.remove(user)
                if str(reaction) == conf.lang(lang, "ok-emoji"):
                    await give_a_drink(ctx, user, drink)
        await msg.delete()
        log.info("Deleted message {0} on {1} by time exceeding".format(msg.id, ctx.guild.id))

    @serve.error
    async def serve_error(self, ctx, error):
        lang = get_lang_from_context(ctx)
        if isinstance(error, commands.BotMissingPermissions):
            await ctx.send(conf.lang(lang, "missing_permissions", "serve"))
            error.bcdb_checked = True

    @commands.command()
    @commands.has_role("barman")
    @commands.guild_only()
    async def reset(self, ctx: Context, to_defaults: bool = False):
        """
        Reset all drinks to defaults. Barman role required.
        """
        server = get_server_from_context(ctx)
        lang = server.lang
        Drink.delete().where(Drink.server == server).execute()
        if to_defaults:
            await add_default_drinks(ctx.guild)
            await ctx.send(conf.lang(lang, "reset_to_defaults_complete"))
        else:
            await ctx.send(conf.lang(lang, "reset_complete"))

    @reset.error
    @not_barman
    def reset_error(self, ctx, error):
        pass


def setup(bot):
    bot.add_cog(DrinkCog(bot))

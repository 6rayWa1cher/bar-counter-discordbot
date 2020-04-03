import discord
from discord.ext import commands
from discord.utils import find

from barcounter import log

logger = log

ROLE_NAME = "barman"


def is_role_powered(ctx):
    rl = find(lambda r: r.name == ROLE_NAME, ctx.author.roles)
    return rl is not None


def get_role(bot: discord.ext.commands.Bot, guild: discord.Guild):
    return bot.cogs["RoleRegistrarCog"].guild_to_role[guild]


class RoleRegistrarCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.guild_to_role = dict()

    async def bot_check_once(self, ctx):
        return await self.on_guild_join(ctx.guild)

    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        if guild not in self.guild_to_role:
            self.guild_to_role[guild] = await self._check_role_existence(guild)
        return True

    @staticmethod
    async def _check_role_existence(guild):
        if ROLE_NAME not in map(lambda x: x.name, guild.roles):
            logger.info("creating role in {0.id} guild".format(guild))
            return await guild.create_role(name=ROLE_NAME, permissions=discord.Permissions.none())
        else:
            return find(lambda a: a.name == ROLE_NAME, guild.roles)


def setup(bot):
    bot.add_cog(RoleRegistrarCog(bot))

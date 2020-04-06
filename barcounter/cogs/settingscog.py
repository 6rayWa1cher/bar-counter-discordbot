from discord.ext import commands
from discord.ext.commands import Bot, Context

from barcounter import confutils as conf, db
from barcounter import log
from barcounter.cogs.helpers import get_server_or_create, add_default_drinks, get_lang_from_context
from barcounter.confutils import get_langs
from barcounter.dbentities import Server, Drink

logger = log


class SettingsCog(commands.Cog):
    def __init__(self, bot):
        self.bot: Bot = bot

    @commands.Cog.listener()
    async def on_command_error(self, ctx: Context, error):
        if not hasattr(error, "bcdb_checked") or not error.bcdb_checked:
            log.error("Error on command {0}".format(ctx.command), exc_info=error)
            await ctx.send(conf.lang(get_lang_from_context(ctx), "on_error"))
        return True

    @commands.group()
    @commands.guild_only()
    @commands.has_permissions(manage_guild=True)
    async def lang(self, ctx: Context, lang_code: str = None):
        """
        If lang is provided, sets the language. Requires Manage Guild permission.
        Return the list of available languages and quick reminder how to set it.
        """
        if lang_code:
            if lang_code not in get_langs():
                await ctx.send(conf.international("incorrect_language"))
            else:
                logger.info("Updated lang on {0} to {1}".format(ctx.guild.id, lang_code))
                with db.atomic():
                    server = get_server_or_create(ctx.guild.id, ctx.guild.preferred_locale)
                    Server.update(lang=lang_code).where(Server.sid == ctx.guild.id).execute()
                    Drink.delete().where(Drink.server == server.id).execute()
                    await add_default_drinks(ctx.guild)
                await ctx.send(conf.lang(lang_code, "lang_selected"))
        else:
            langs = "\n".join(
                "{0}, lang_code \"{1}\"".format(conf.lang(lang, "name"), lang) for lang in conf.get_langs())
            await ctx.send(conf.international("lang_list").format(self.bot.command_prefix) + '\n' + langs)

    @lang.error
    async def lang_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send(conf.international("missing_permissions"))


async def globally_block_dms(ctx):
    return ctx.guild is not None


def setup(bot):
    bot.add_check(globally_block_dms)
    bot.add_cog(SettingsCog(bot))

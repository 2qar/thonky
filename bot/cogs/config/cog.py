from discord.ext import commands
from discord.ext.commands import Context
from ...dbhandler import DBHandler
import re

base_sheet_url = 'https://docs.google.com/spreadsheets/d/'


def write_property(server_id, key, value):
    """ Update a single property of a server's config """
    with DBHandler() as handler:
        handler.update_server_config(server_id, key, value)


class Config:
    def __init__(self, bot):
        self.bot = bot

    @commands.command(pass_context=True)
    async def set_sheet(self, ctx: Context, url: str):
        sheet_re_raw = 'https:\/\/docs.google.com\/spreadsheets\/d\/[\d\w-]{44}'
        sheet_re = re.compile(sheet_re_raw)
        if not sheet_re.match(url):
            await ctx.send("Invalid spreadsheet url.")
        else:
            # cut the stuff surrounding the key
            doc_key = url[len(base_sheet_url):]
            doc_key = doc_key[:doc_key.find('/')]

            write_property(ctx.guild.id, 'doc_key', doc_key)

            server_info = self.bot.server_info[str(ctx.guild.id)]
            await server_info.update(channel=ctx.channel)

    @commands.command(pass_context=True)
    async def set_channel(self, ctx: Context, channel: str):
        channel_re_raw = '<#\d{18}>'
        channel_re = re.compile(channel_re_raw)
        if not channel_re.match(channel):
            await ctx.send("Invalid channel.")
        else:
            channel_id = channel[2:len(channel)-1]
            channel_obj = ctx.guild.get_channel(int(channel_id))
            if channel_obj:
                if not channel_obj.permissions_for(ctx.guild.me).send_messages:
                    await ctx.send("I can't send messages in that channel. :(")
                else:
                    write_property(ctx.guild.id, 'announce_channel', channel_id)
                    await ctx.send("Channel set. :)")
            else:
                await ctx.send("I can't see that channel. :(")


def setup(bot):
    bot.add_cog(Config(bot))

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
        sheet_re = 'https:\/\/docs.google.com\/spreadsheets\/d\/[\d\w-]{44}'
        if not re.match(sheet_re, url):
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
        if not re.match('<#\d{18}>', channel):
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

    @commands.command(pass_context=True)
    async def set_team(self, ctx: Context, team_url: str):
        match = re.match('https:\/\/battlefy.com\/teams\/[\d\w]{24}', team_url)
        if not match:
            await ctx.send("Invalid team link.")
        else:
            team_url = match.group(0)
            team_id = team_url[team_url.rfind('/') + 1::]
            with DBHandler() as handler:
                handler.update_server_config(ctx.guild.id, 'team_id', team_id)
            await ctx.send("Team set. :)")

    @commands.command(pass_context=True, name='set_tourney')
    async def set_tournament(self, ctx: Context, tournament_url: str):
        tournament_re = 'https:\/\/battlefy.com/overwatch-open-division-north-america\/[\w\d-]{1,}\/[\d\w]{24}'
        match = re.match(tournament_re, tournament_url)
        if not match:
            await ctx.send("Invalid tournament url.")
        else:
            url = match.group(0)
            with DBHandler() as handler:
                handler.update_server_config(ctx.guild.id, 'tournament_link', url)
            await ctx.send("Tournament set. :)")


def setup(bot):
    bot.add_cog(Config(bot))

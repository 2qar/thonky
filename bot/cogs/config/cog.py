import aiohttp
from discord.ext import commands
from discord.ext.commands import Context
from discord import Embed, Color
import re

from ...dbhandler import DBHandler
from ...formatter import thonk_link, sheet_url

base_sheet_url = 'https://docs.google.com/spreadsheets/d/'


def write_property(server_id, key, value):
    """ Update a single property of a server's config """
    with DBHandler() as handler:
        handler.update_server_config(server_id, key, value)


def get_last_link_element(link: str) -> str:
    """ Get the thing at the end of a link path.

        Passing this link:
            https://battlefy.com/teams/5bfe1b9418ddd9114f14efb0
        Would return:
            5bfe1b9418ddd9114f14efb0
    """
    return link[link.rfind('/') + 1::]


class Config:
    def __init__(self, bot):
        self.bot = bot

    @commands.command(pass_context=True)
    async def set_sheet(self, ctx: Context, url: str):
        """ Sets the sheet to grab schedule info from.

            Make a sheet using a copy of this template:
                https://docs.google.com/spreadsheets/d/1_78Wbe8EeaBC4Dc1X3bXyHyfC5BKCFm2VuxQlljeYMQ/edit?usp=sharing
        """

        sheet_re = 'https://docs.google.com/spreadsheets/d/[\d\w-]{44}'
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
        """ Sets the channel to send reminder messages in. """

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
    async def set_role(self, ctx: Context, role_mention: str):
        """ Sets the role to ping in reminder messages.

            Mention a role...
                !set @everyone
            or give the name of a role...
                !set Default
            role names with more than 1 word need quotes
                !set "Default Role"
        """

        async def write_role(mention: str):
            write_property(ctx.guild.id, 'role_mention', mention)
            await ctx.send("Role set. :)")

        if re.match('<@&\d{18}>', role_mention):
            await write_role(role_mention)
        else:
            for role in ctx.guild.roles:
                if role.name.lower() == role_mention.lower():
                    await write_role(role.mention)
                    return
            await ctx.send(f"Invalid role \"{role_mention}\". :(")

    @commands.command(pass_context=True)
    async def set_team(self, ctx: Context, team_url: str):
        """ Sets the team on Battlefy to look for in matches. """

        match = re.match('https://battlefy.com/teams/[\d\w]{24}', team_url)
        if not match:
            await ctx.send("Invalid team link.")
        else:
            team_url = match.group(0)
            team_id = get_last_link_element(team_url)
            with DBHandler() as handler:
                handler.update_server_config(ctx.guild.id, 'team_id', team_id)
            await ctx.send("Team set. :)")

    @commands.command(pass_context=True, name='set_tourney')
    async def set_tournament(self, ctx: Context, tournament_url: str):
        """ Sets the tournament stage ID for grabbing match info..

            The link must follow this format:
                https://battlefy.com/{organization}/{tournament}/{tournament_id}/stage/{stage_id}
        """

        tournament_re = 'https://battlefy.com/[\w\d-]{1,}/[\w\d-]{1,}/[\d\w]{24}/stage/[\d\w]{24}'
        match = re.match(tournament_re, tournament_url)
        if not match:
            await ctx.send("Invalid tournament url.")
        else:
            url = match.group(0)
            stage_id = get_last_link_element(url)
            with DBHandler() as handler:
                handler.update_server_config(ctx.guild.id, 'stage_id', stage_id)
            await ctx.send("Tournament set. :)")

    @commands.command(pass_context=True)
    async def set_update(self, ctx: Context, update_interval: str):
        """ Set the sheet update interval (in minutes). """
        try:
            interval = int(update_interval)
        except ValueError:
            await ctx.send(f"\"{update_interval}\" isn't a number. :(")
            return

        limit = 5
        if interval < limit:
            await ctx.send(f"Less than {limit} minutes is too quick. :(")
        else:
            write_property(ctx.guild.id, 'update_interval', interval)
            await ctx.send("Update interval set. :)")

    @commands.command(pass_context=True)
    async def show_config(self, ctx: Context):
        embed = Embed(colour=Color.from_rgb(255, 204, 77))
        embed.set_author(name=f"Config for {ctx.guild.name}", icon_url=ctx.guild.icon_url)
        embed.set_thumbnail(url=thonk_link)

        with DBHandler() as handler:
            config = handler.get_server_config(ctx.guild.id)

        embed.set_thumbnail(url=f"{sheet_url}{config['doc_key']}")

        def add_field(name: str, value: str): embed.add_field(name=name, value=value, inline=False)

        add_field("Reminder Channel", self.bot.get_channel(int(config['announce_channel'])).mention)
        add_field("Reminder Ping", config['role_mention'])
        add_field("Reminder Activities", ', '.join(config['remind_activities']))
        add_field("Intervals", ', '.join([str(item) for item in config['remind_intervals']]))
        add_field("Sheet Update Interval", config['update_interval'])

        session = aiohttp.ClientSession()

        async def get_json(url: str) -> dict:
            async with session.get(url, headers={'User-Agent': 'thonky'}) as response:
                return await response.json()

        tournament_json = await get_json(
            f"https://dtmwra1jsgyb0.cloudfront.net/stages/{config['stage_id']}?extend[groups][teams]=true"
        )
        tournament_name = tournament_json[0]['name']
        add_field("Tournament Name", tournament_name)

        team_info = await get_json(f"https://dtmwra1jsgyb0.cloudfront.net/persistent-teams/{config['team_id']}")
        team_name = team_info[0]['name']
        team_link = f"https://battlefy.com/teams/{team_info[0]['_id']}"
        add_field("Team", f"{team_name}\n{team_link}")

        await session.close()

        await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(Config(bot))

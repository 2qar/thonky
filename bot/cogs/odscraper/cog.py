from discord.ext import commands
from discord import Embed, Colour
import asyncio

from .scraper import get_other_team_info
from ...dbhandler import DBHandler
from ...formatter import role_emotes

battlefy_logo = 'http://s3.amazonaws.com/battlefy-assets/helix/images/logos/logo.png'

overbuff_role_emotes = {
    "Offense": role_emotes['DPS'],
    "Defense": role_emotes['DPS'],
    "Tank": role_emotes['Tanks'],
    "Support": role_emotes['Supports'],
    "???": ":ghost:"
}


class ODScraper:
    def __init__(self, bot):
        self.bot = bot

    @staticmethod
    async def get_info_from_id(od_round, server_id):
        with DBHandler() as handler:
            config = handler.get_server_config(server_id)
        if config:
            return await get_other_team_info(od_round, config['team_id'])

    @staticmethod
    def format_other_team_info(od_round, team_info):
        title = f"Match against {team_info['name']} in Round {od_round}"
        embed = Embed()
        embed.colour = Colour.red()
        embed.set_author(
            name=title, 
            url=team_info['match_link'],
            icon_url=battlefy_logo
        )

        embed.set_thumbnail(url=team_info['logo'])
        
        players_with_info = [player for player in team_info['players'] if player['info']]
        players = sorted(players_with_info, key=lambda k: k['info'].get_sr(), reverse=True)

        def format_player_info(player: dict) -> str:
            if not player['info']:
                return ":ghost: " + player['name']
            else:
                role_emote = overbuff_role_emotes[player['info'].get_role()[0]]
                sr = player['info'].get_sr()
                if sr == 0:
                    sr = '???'
                return f"{role_emote} {player['name']}: {sr}"

        player_string = '\n'.join([format_player_info(player) for player in team_info['players']])

        def get_top_average():
            top_players = players[:6]

            avg = 0
            for player in top_players:
                avg += player['info'].get_sr()

            return int(avg / len(top_players))

        if len(players) >= 6:
            average_sr = f"**Average SR: {team_info['sr_avg']}**\n"
            player_string = average_sr + player_string
            
            top_average = f"Top 6 Average: {get_top_average()}"
            embed.add_field(name=top_average, value=player_string)
        else:
            embed.add_field(name=f"Average SR: {team_info['sr_avg']}")

        return embed

    @staticmethod
    async def send_od(ctx, od_round):
        try:
            int(od_round)
        except ValueError:
            await ctx.send("Invalid round number.")
            return

        message = await ctx.send("Getting match info...")

        enemy_info = await ODScraper.get_info_from_id(od_round, ctx.guild.id)
        if enemy_info:
            embed = ODScraper.format_other_team_info(od_round, enemy_info)
            await message.edit(content=None, embed=embed)
        else:
            await ctx.send("No OD team ID set.")

    @commands.command(pass_context=True)
    async def od(self, ctx, od_round):
        await ODScraper.send_od(ctx, od_round)


def setup(bot):
    bot.add_cog(ODScraper(bot))

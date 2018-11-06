from discord.ext import commands
import asyncio

from .scraper import get_other_team_info
from ...dbhandler import DBHandler

class ODScraper:
    def __init__(self, bot):
        self.bot = bot

    async def get_info_from_id(od_round, server_id):
        with DBHandler() as handler:
            config = handler.get_server_config(server_id)
        if config:
            return get_other_team_info(od_round, config['team_id'])

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
        players =  sorted(players_with_info, key=lambda k: k['info']['sr'], reverse=True)

        def format_player_info(player):
            if not player['info']:
                return ":ghost: " + player['name']
            else:
                role_emote = overbuff_role_emotes[player['info'].get_role()[0]]
                sr = player['info'].get_sr()
                if sr == 0: sr = '???'
                return f"{role_emote} {player['name']}: {sr}"

        player_string = '\n'.join([format_player_info(player) for player in team_info['players']])

        def get_top_average():
            top_players = players[:6]

            avg = 0
            for player in top_players:
                avg += player['info']['sr']

            return int(avg / len(top_players))

        if len(players) >= 6:
            average_sr = f"**Average SR: {team_info['sr_avg']}**\n"
            player_string = average_sr + player_string
            
            top_average = f"Top 6 Average: {get_top_average()}"
            embed.add_field(name=top_average, value=player_string)
        else:
            embed.add_field(name=f"Average SR: {team_info['sr_avg']}")

        return embed

    @commands.command()
    async def od(self, ctx, round_num):
        channel = ctx.message.channel

        try:
            int(round_num)
        except:
            channel.send("Invalid round number.")
            return

        enemy_info = ODScraper.get_info_from_id(ctx.server.id)
        if info:
            embed = ODScraper.format_other_team_info(round_num, enemy_info)
            channel.send(embed=embed)
        else:
            channel.send("No OD team ID set.")

def setup(bot):
    bot.add_cog(ODScraper(bot))

from discord.ext import commands
from discord import Embed, Colour

from .scraper import get_other_team_info, find_team
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
        
        players_with_info = [player for player in team_info['players'] if player['info'] is not None]
        players = sorted(players_with_info, key=lambda k: k['info'].get_sr(), reverse=True)

        def format_player_info(player: dict) -> str:
            if not player['info']:
                return ":ghost: " + player['name']
            else:
                main_role = player['info'].get_role()
                if main_role:
                    role_emote = overbuff_role_emotes[main_role[0]]
                else:
                    role_emote = ':ghost:'
                sr = player['info'].get_sr()
                if sr == 0:
                    sr = '???'
                name = player['name'] if not player['active'] else f"**{player['name']}**"
                return f"{role_emote} {name}: {sr}"

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
            embed.add_field(name=f"Average SR: {team_info['sr_avg']}", value=player_string)

        return embed

    @staticmethod
    async def send_od(info, ctx, od_round):
        try:
            int(od_round)
        except ValueError:
            await ctx.send("Invalid round number.")
            return

        config = info.config
        stage_id = config['stage_id']
        team_id = config['team_id']

        if not stage_id and not team_id:
            await ctx.send("No tournament or team set. :(")
        elif not stage_id:
            await ctx.send("No tournament set. :(")
        elif not team_id:
            await ctx.send("No team set. :(")
        else:
            message = await ctx.send("Getting match info...")

            enemy_info = await get_other_team_info(stage_id, od_round, team_id)
            if enemy_info:
                embed = ODScraper.format_other_team_info(od_round, enemy_info)
                await message.edit(content=None, embed=embed)
            else:
                await message.edit(content=f"No data for round {od_round}. :(")

    @commands.command(pass_context=True)
    async def od(self, ctx, od_round):
        await ODScraper.send_od(self.bot.get_info(ctx), ctx, od_round)

    @commands.command(pass_context=True)
    async def team(self, ctx, name):
        info = self.bot.get_info(ctx)
        tournament_link = info.config['tournament_link']
        if not tournament_link:
            await ctx.send("No tournament link set.")
            return

        teams = await find_team(tournament_link, name)
        if not teams:
            await ctx.send("No results. :(")
            return

        team_names = '\n'.join([team['name'] for team in teams])
        formatted_teams = f"```\n{team_names}\n```"
        await ctx.send(formatted_teams)


def setup(bot):
    bot.add_cog(ODScraper(bot))

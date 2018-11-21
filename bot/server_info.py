from discord import NotFound
from calendar import day_name as day_names

from .sheetbot import SheetScraper
from .ping_scheduler import PingScheduler
from .dbhandler import DBHandler


class ServerInfo:
    def __init__(self, guild_id, config, bot):
        self.guild_id = guild_id
        self.config = config
        self.bot = bot

        self.scraper = SheetScraper(config['doc_key'])
        self.players = self.scraper.get_players()
        self.week_schedule = self.scraper.get_week_schedule()
        self.scheduler = PingScheduler(guild_id, self)
        self.scheduler.init_scheduler(self)

        self.scanning = False

    def get_ping_channel(self):
        with DBHandler() as handler:
            channel_id = handler.get_server_config(self.guild_id)['announce_channel']
            try:
                return self.bot.get_channel(channel_id)
            except NotFound:
                return None

    def save_players(self):
        week = self.week_schedule[0].replace('/', '-')

        with DBHandler() as handler:
            for player in self.players.unsorted_list:
                if not handler.get_player_data(self.guild_id, player.name, date=week):
                    availability = {}
                    for day, day_name in enumerate(day_names):
                        availability[day_name] = player.get_availability_for_day(day)
                    handler.add_player_data(self.guild_id, player.name, week, availability)
                    print(f"added {player.name} on {week} to db")
                else:
                    print(f"{player.name} on {week} already added, skipping")

    async def update(self, channel=None):
        async def try_send(msg):
            if channel:
                await channel.send(msg)

        if self.scanning:
            await try_send("Already updating.")
            return
        else:
            await try_send("Updating...")

        self.scanning = True

        scraper = self.scraper
        scraper.authenticate()
        self.players = scraper.get_players()
        self.week_schedule = scraper.get_week_schedule()

        ping_channel = self.get_ping_channel()
        if ping_channel:
            self.scheduler.init_schedule_pings(ping_channel)

        self.scanning = False
        await try_send("Finished updating. :)")

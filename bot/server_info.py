from discord import NotFound

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

        self.scanning = True

    def get_ping_channel(self):
        with DBHandler() as handler:
            channel_id = handler.get_server_config()['announce_channel']
            try:
                return self.bot.get_channel(channel_id)
            except NotFound:
                return None

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
        self.scheduler.init_schedule_pings(self.bot)

        self.scanning = False
        await try_send("Finished updating. :)")

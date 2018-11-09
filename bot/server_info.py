from .sheetbot import SheetScraper
from .ping_scheduler import PingScheduler

class ServerInfo:
    def __init__(self, doc_key, server_id, bot, update_command):
        self.bot = bot

        self.scraper = SheetScraper(doc_key)
        self.players = self.scraper.get_players()
        self.week_schedule = self.scraper.get_week_schedule()
        self.scanning = False
        self.scheduler = PingScheduler(server_id, self)
        self.update_command = update_command
        self.scheduler.init_scheduler(bot, update_command)

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

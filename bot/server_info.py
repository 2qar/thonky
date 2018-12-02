from discord import NotFound
from calendar import day_name as day_names

from .sheetbot import SheetHandler
from .ping_scheduler import PingScheduler
from .dbhandler import DBHandler


class ServerInfo:
    def __init__(self, guild_id, config, bot):
        self.guild_id = guild_id
        self.config = config
        self.bot = bot

        self.sheet_handler = SheetHandler(config['doc_key'])
        self.players = self.sheet_handler.get_players()
        self.week_schedule = self.sheet_handler.get_week_schedule()
        self.valid_activities = self.sheet_handler.get_valid_activities()
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

        with DBHandler() as handler:
            doc_key = handler.get_server_config(self.guild_id)['doc_key']
            if not doc_key:
                await try_send('No spreadsheet given for this server :(')
                return

        self.scanning = True

        handler = SheetHandler(doc_key)
        handler.authenticate()
        self.players = handler.get_players()
        self.week_schedule = handler.get_week_schedule()
        self.valid_activities = handler.get_valid_activities()

        ping_channel = self.get_ping_channel()
        if ping_channel:
            self.scheduler.init_schedule_pings(ping_channel)

        self.scanning = False
        await try_send("Finished updating. :)")

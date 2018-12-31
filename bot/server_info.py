from abc import abstractmethod, ABC
from discord import NotFound
from calendar import day_name as day_names
from apscheduler.jobstores.memory import MemoryJobStore

from .sheetbot import SheetHandler
from .dbhandler import DBHandler


class BaseInfo(ABC):
    def _init_sheet(self, doc_key: str):
        self.sheet_handler = SheetHandler(doc_key)
        self._init_sheet_attrs()

    def _init_sheet_attrs(self):
        self.players = self.sheet_handler.get_players()
        self.week_schedule = self.sheet_handler.get_week_schedule()
        self.valid_activities = self.sheet_handler.get_valid_activities()

    def __init__(self, guild_id, config, bot):
        self.guild_id = guild_id
        self.config = config
        self.bot = bot

        self.jobstores = {
            "maintenance": MemoryJobStore(),
            "pings": MemoryJobStore()
        }

        if self.config['doc_key']:
            self._init_sheet(self.config['doc_key'])
            bot.ping_scheduler.setup_guild(self)
        else:
            self.sheet_handler = None
            self.players = None
            self.week_schedule = None
            self.valid_activities = None

        self.scanning = False

    @abstractmethod
    def get_id(self):
        """ Get something to use as an ID for jobstores in PingScheduler """
        pass

    @abstractmethod
    def get_config(self):
        pass

    def get_ping_channel(self):
        channel_id = self.get_config()['announce_channel']
        try:
            return self.bot.get_channel(channel_id)
        except NotFound:
            return None

    def save_players(self):
        week = self.week_schedule[0].date.replace('/', '-')

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

        if self.sheet_handler is not None:
            if self.sheet_handler.updated:
                await try_send("Nothing to update.")
                return

        if self.scanning:
            await try_send("Already updating.")
            return
        else:
            await try_send("Updating...")

        doc_key = self.get_config()['doc_key']
        if not doc_key:
            await try_send('No spreadsheet given for this server :(')
            return

        self.scanning = True

        if not self.sheet_handler:
            self._init_sheet(doc_key)
        else:
            self.sheet_handler.doc_key = doc_key
            self._init_sheet_attrs()

        ping_channel = self.get_ping_channel()
        has_jobstores = self.bot.ping_scheduler.has_info_jobstores(self)
        if ping_channel and has_jobstores:
            self.bot.ping_scheduler.init_schedule_pings(self.get_ping_channel(), self)
        elif not has_jobstores:
            self.bot.ping_scheduler.setup_guild(self)

        self.scanning = False
        self.sheet_handler.update_modified()
        await try_send("Finished updating. :)")


class TeamInfo(BaseInfo):
    def __init__(self, guild_id, config, bot):
        super().__init__(guild_id, config, bot)

    def get_id(self):
        return self.config['team_name'].lower()

    def get_config(self):
        with DBHandler() as handler:
            return handler.get_team_config(self.get_id())


class GuildInfo(BaseInfo):
    def __init__(self, guild_id, config, bot):
        super().__init__(guild_id, config, bot)

    def get_id(self):
        return self.guild_id

    def get_config(self):
        with DBHandler() as handler:
            return handler.get_server_config(self.guild_id)

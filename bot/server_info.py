from abc import abstractmethod, ABC
from discord import NotFound
from calendar import day_name as day_names
from apscheduler.jobstores.memory import MemoryJobStore

from .sheetbot import Sheet
from .dbhandler import DBHandler


class BaseInfo(ABC):
    async def _init_sheet(self, doc_key: str):
        self.sheet: Sheet = await self.bot.sheet_handler.get_sheet(doc_key)
        await self._init_sheet_attrs()

    async def _init_sheet_attrs(self):
        self.players = await self.sheet.get_players()
        self.week_schedule = await self.sheet.get_week_schedule()
        self.valid_activities = self.sheet.get_valid_activities()

    def __init__(self, guild_id, config, bot):
        self.guild_id = guild_id
        self.config = config
        self.bot = bot

        self.jobstores = {
            "maintenance": MemoryJobStore(),
            "pings": MemoryJobStore()
        }

        self.sheet = None
        self.players = None
        self.week_schedule = None
        self.valid_activities = None

        self.scanning = False

    async def init_sheet(self):
        doc_key = self.config['doc_key']
        if doc_key:
            await self._init_sheet(doc_key)
            self.bot.ping_scheduler.setup_guild(self)

    @property
    def sheet_link(self):
        return f"https://docs.google.com/spreadsheets/d/{self.config['doc_key']}"

    @abstractmethod
    def get_id(self):
        """ Get something to use as an ID for jobstores in PingScheduler """
        pass

    def update_config(self, key, value):
        self.config[key] = value
        self._update_config(key, value)

    @abstractmethod
    def _update_config(self, key, value):
        pass

    def get_ping_channel(self):
        channel_id = self.config['announce_channel']
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

        if self.scanning:
            await try_send("Already updating.")
            return
        else:
            await try_send("Updating...")

        doc_key = self.config['doc_key']
        if not doc_key:
            await try_send('No spreadsheet given for this server :(')
            return
        elif self.sheet:
            if doc_key == self.sheet.id and self.sheet.updated:
                await try_send("Nothing to update.")
                return

        self.scanning = True

        if not self.sheet:
            await self._init_sheet(doc_key)
        else:
            await self._init_sheet_attrs()

        ping_channel = self.get_ping_channel()
        has_jobstores = self.bot.ping_scheduler.has_info_jobstores(self)
        if ping_channel and has_jobstores:
            self.bot.ping_scheduler.update_schedule_pings(self.week_schedule, self)
        elif not has_jobstores:
            self.bot.ping_scheduler.setup_guild(self)

        self.scanning = False
        self.sheet.update_modified()
        await try_send("Finished updating. :)")


class TeamInfo(BaseInfo):
    def __init__(self, guild_id, config, bot):
        super().__init__(guild_id, config, bot)

    def get_id(self):
        return self.team_name.lower()

    def _update_config(self, key, value):
        with DBHandler() as handler:
            handler.update_team_config(self.guild_id, self.team_name, key, value)

    def has_channel(self, channel_id: int):
        return channel_id in [int(channel) for channel in self.config['channels']]

    @property
    def team_name(self):
        return self.config['team_name']


class GuildInfo(BaseInfo):
    def __init__(self, guild_id, config, bot):
        super().__init__(guild_id, config, bot)

        def get_team_info(team_config): return TeamInfo(guild_id, team_config, bot)
        with DBHandler() as handler:
            self._teams = [get_team_info(team_config) for team_config in handler.get_teams(guild_id)]

    async def init_team_sheets(self):
        for team in self._teams:
            await team.init_sheet()

    def get_id(self):
        return self.guild_id

    def _update_config(self, key, value):
        with DBHandler() as handler:
            handler.update_server_config(self.guild_id, key, value)

    def get_team_in_channel(self, channel_id: int) -> TeamInfo or None:
        for team in self._teams:
            if team.has_channel(channel_id):
                return team

    def add_team(self, config: dict):
        self._teams.append(TeamInfo(self.guild_id, config, self.bot))

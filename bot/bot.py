from discord.ext.commands import Context, Bot as DiscordBot
from discord import Game
import importlib
import os
from typing import Union, Dict

from .server_info import GuildInfo, TeamInfo
from .ping_scheduler import PingScheduler
from .sheetbot import SheetHandler
from .dbhandler import DBHandler


# TODO: Maybe write spreadsheet info to the disk so the sheets dont have to get scanned every time the bot is booted


class Bot(DiscordBot):
    def __init__(self, token):
        super().__init__('!')
        self.server_info: Dict[str, GuildInfo] = {}
        self.ping_scheduler = PingScheduler()
        self.sheet_handler: SheetHandler = SheetHandler()
        self.run(token)

    def add_cogs(self):
        for cog in os.listdir('bot/cogs'):
            if os.path.exists(f'bot/cogs/{cog}/cog.py'):
                module = importlib.import_module(f'.cogs.{cog}.cog', package='bot')
                getattr(module, 'setup')(self)

    async def get_server_info(self):
        with DBHandler() as handler:
            for guild in self.guilds:
                await self.create_guild_info(guild.id, handler)

    async def on_ready(self):
        playing = Game("with spreadsheets")
        self.add_cogs()
        await self.sheet_handler.init()
        await self.get_server_info()

        await self.change_presence(activity=playing)
        print("Ready! :)")
            
    async def on_guild_join(self, guild):
        await self.wait_until_ready()

        with DBHandler() as handler:
            await self.create_guild_info(guild.id, handler)
        # send a message that's like "hey admins you should !set_sheet and !set_team"
        # also mention the default settings
        # also mention setting the ping channel

    async def create_guild_info(self, guild_id: Union[str, int], handler):
        config = handler.get_server_config(guild_id)

        if config:
            guild_info = GuildInfo(guild_id, config, self)
            self.server_info[str(guild_id)] = guild_info
            await guild_info.init_sheet()
            await guild_info.init_team_sheets()
        else:
            handler.add_server_config(guild_id)
            await self.create_guild_info(guild_id, handler)

    def get_info(self, ctx: Context) -> GuildInfo or TeamInfo:
        guild_info = self.server_info[str(ctx.guild.id)]
        team_info = guild_info.get_team_in_channel(ctx.channel.id)
        if team_info:
            return team_info
        else:
            return guild_info

from discord.ext.commands import Bot as DiscordBot
from discord import Game
import importlib
import os
from typing import Union

from .server_info import ServerInfo
from .ping_scheduler import PingScheduler
from .dbhandler import DBHandler


# TODO: Maybe write spreadsheet info to the disk so the sheets dont have to get scanned every time the bot is booted


class Bot(DiscordBot):
    def __init__(self, token):
        super().__init__('!')
        self.server_info = {}
        self.ping_scheduler = PingScheduler()
        self.run(token)

    def add_cogs(self):
        for cog in os.listdir('bot/cogs'):
            if os.path.exists(f'bot/cogs/{cog}/cog.py'):
                module = importlib.import_module(f'.cogs.{cog}.cog', package='bot')
                getattr(module, 'setup')(self)

    def get_server_info(self):
        with DBHandler() as handler:
            for guild in self.guilds:
                self.create_guild_info(guild.id, handler)

    async def on_ready(self):
        playing = Game("with spreadsheets")
        self.add_cogs()
        self.get_server_info()

        await self.change_presence(activity=playing)
        print("Ready! :)")
            
    async def on_guild_join(self, guild):
        await self.wait_until_ready()

        with DBHandler() as handler:
            self.create_guild_info(guild.id, handler)
        # send a message that's like "hey admins you should !set_sheet and !set_team"
        # also mention the default settings
        # also mention setting the ping channel

    def create_guild_info(self, guild_id: Union[str, int], handler):
        config = handler.get_server_config(guild_id)

        if config:
            self.server_info[str(guild_id)] = ServerInfo(guild_id, config, self)
        else:
            handler.add_server_config(guild_id)
            self.create_guild_info(guild_id, handler)

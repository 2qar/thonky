from discord.ext.commands import Bot as DiscordBot
from discord import Game
import importlib
import os
from typing import Union

from .server_info import ServerInfo
from .dbhandler import DBHandler

# TODO: Rewrite sheetbot and odscraper as modules with their own formatters
'''
bot
    modules
        odscraper
            odformatter
            functionality stuff
        sheetbot
            sheet_formatter
            functionality stuff

    Pass the bot and channel to the formatter and the formatter constructs embeds AND sends the message
'''

# TODO: Maybe write spreadsheet info to the disk so the sheets dont have to get scanned every time the bot is booted


class Bot(DiscordBot):
    def __init__(self, token):
        super().__init__('!')
        self.server_info = {}
        self.run(token)

    def add_cogs(self):
        for cog in os.listdir('bot/cogs'):
            if os.path.exists(f'bot/cogs/{cog}/cog.py'):
                module = importlib.import_module(f'.cogs.{cog}.cog', package='bot')
                getattr(module, 'setup')(self)

    def get_server_info(self):
        with DBHandler() as handler:
            for guild in self.guilds:
                self.create_guild_info(guild.id, handler=handler)

    async def on_ready(self):
        playing = Game("with spreadsheets")
        self.add_cogs()
        self.get_server_info()

        await self.change_presence(activity=playing)
        print("Ready! :)")
            
    async def on_guild_join(self, guild):
        await self.wait_until_ready()

        self.create_guild_info(guild.id)
        # send a message that's like "hey admins you should !set_sheet and !set_team"
        # also mention the default settings
        # also mention setting the ping channel

    @staticmethod
    def create_guild_config(guild_id: Union[str, int], handler=None):
        print(f"Creating config for server with ID [{guild_id}]")

        if handler:
            if not handler.get_server_config(guild_id):
                handler.add_server_config(guild_id)
        else:
            with DBHandler() as handler:
                if not handler.get_server_config(guild_id):
                    handler.add_server_config(guild_id)

    def create_guild_info(self, guild_id: Union[str, int], handler=None):
        if handler:
            config = handler.get_server_config(guild_id)
        else:
            with DBHandler() as handler:
                config = handler.get_server_config(guild_id)
        if config:
            doc_key = config['doc_key']
            if doc_key:
                self.server_info[str(guild_id)] = ServerInfo(guild_id, config, self)
        else:
            Bot.create_guild_config(guild_id, handler=handler)

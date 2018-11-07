from discord.ext.commands import Bot as DiscordBot
import asyncio
import importlib
import os

from .server_info import ServerInfo
from .dbhandler import DBHandler

#TODO: Rewrite sheetbot and odscraper as modules with their own formatters
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

#TODO: Maybe write spreadsheet info to the disk so the sheets dont have to get scanned every time the bot is booted

class Bot(DiscordBot):
    def __init__(self, token):
        super().__init__('!')
        self.run(token)

    def add_cogs(self):
        for cog in os.listdir('bot/cogs'):
            if os.path.exists(f'bot/cogs/{cog}/cog.py'):
                module = importlib.import_module(f'.cogs.{cog}.cog', package='bot')
                getattr(module, 'setup')(self)
    
    async def on_ready(self):
        #playing = discord.Game(name="with spreadsheets", url=sheet_url, type=1)
        #await self.change_presence(game=playing)

        self.add_cogs()

        self.server_info = {}
        with DBHandler() as handler:
            for server in self.servers:
                server_config = handler.get_server_config(server.id)
                if server_config:
                    doc_key = server_config['doc_key']
                    if not doc_key:
                        print(f"No doc_key provided for server \"{server.name}\" with ID [{server.id}].")
                        continue
                    else:
                        self.server_info[server.id] = ServerInfo(doc_key, server.id, self, UpdateCommand.invoke)
                else:
                    print(f"Failed to get config for server \"{server.name}\" with ID [{server.id}].")
                    Bot.create_server_config(server)

        print("Ready! :)")
            
    async def on_server_join(self, server):
            await self.wait_until_ready()

            Bot.create_server_config(server.id)
            # send a message that's like "hey admins you should !set_sheet and !set_team"
            # also mention the default settings
            # also mention setting the ping channel

    def create_server_config(server):
            print(f"Creating config for server with ID [{server.id}]")

            with DBHandler() as handler:
                    if not handler.get_server_config(server.id):
                            handler.add_server_config(server.id)
	
if __name__ == "__main__":
	main()

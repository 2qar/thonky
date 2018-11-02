import discord
import asyncio

from .formatter import sheet_url
from .server_info import ServerInfo
from .dbhandler import DBHandler

#TODO: use discord.ext.commands instead of this garbage
from bot.commands.get_info_command import GetInfoCommand
from bot.commands.update_command import UpdateCommand
import bot.commands.ping_command as ping_cmd
from bot.commands.config_command import config

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

class Bot(discord.Client):
	def __init__(self, token):
			super().__init__()
			self.run(token)
	
	async def on_ready(self):
		playing = discord.Game(name="with spreadsheets", url=sheet_url, type=1)
		await self.change_presence(game=playing)

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
		
	async def on_message(self, message):
		await self.wait_until_ready()

		if ping_cmd.ping_list:
			ping_cmd.check_to_stop(message)

		if message.content.startswith("!"):
			if message.content.startswith("!get"):
				await GetInfoCommand.invoke(self, message)
			elif message.content.startswith("!update"):
				await UpdateCommand.invoke(self, message.server.id, message.channel)
			elif message.content.startswith("!ping"):
				await ping_cmd.ping(self, message)
			elif message.content.startswith("!set"):
				await config(self, message)

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

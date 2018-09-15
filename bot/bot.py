import discord
import asyncio
import json
import shutil
import os
import logging

logger = logging.getLogger('discord')
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler(filename='discord.log', encoding = 'utf-8', mode='w')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)

from .sheetbot import SheetScraper
from .formatter import Formatter
from .formatter import sheet_url
from .ping_scheduler import PingScheduler
from .player_saver import PlayerSaver
from .server_info import ServerInfo

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
	def __init__(self, token, scheduler_config):
			super().__init__()
			self.scheduler_config = scheduler_config
			'''
			self.scraper = SheetScraper()
			self.players = self.scraper.get_players()
			self.week_schedule = self.scraper.get_week_schedule()
			self.scheduler = PingScheduler(scheduler_config)
			self.scheduler.init_auto_update(self)
			self.scheduler.init_save_player_data(self)
			'''
			self.run(token)
	
	async def on_ready(self):
		playing = discord.Game(name="with spreadsheets", url=sheet_url, type=1)
		await self.change_presence(game=playing)

		'''
		SERVER CONFIG FILE NEEDS:
			- doc key
			- server_id
			- announce_channel
			- main_roster_mention

		SERVER DICT NEEDS:
			- all of the above except doc key
			- all of the stuff that the current config has minus tokens and maybe save config
			- scraper
			- players
			- week_schedule
		'''
		self.server_info = {}
		for server in self.servers:
			#TODO: Make this a method so it can be run when the bot joins a server maybe
			server_path = f"servers/{server.id}"
			config_path = f"{server_path}/config.json"
			try:
				#current_info = {}

				server_config = None
				with open(config_path) as file:
					print(config_path)
					server_config = json.load(file)

				doc_key = server_config['doc_key']
				if not doc_key:
					print(f"No doc_key provided for server \"{server.name}\" with ID [{server.id}].")
					continue
				'''
				scraper = SheetScraper(doc_key)
				current_info['scraper'] = scraper
				current_info['players'] = scraper.get_players()
				current_info['week_schedule'] = scraper.get_week_schedule()
				current_info['scanning'] = False
				current_info['scheduler'] = PingScheduler(server.id, self.scheduler_config, current_info)
				
				self.server_info[server.id] = current_info
				'''
				self.server_info[server.id] = ServerInfo(doc_key, server.id, self, UpdateCommand.invoke)
				#current_info['scheduler'].init_scheduler(self)
			except FileNotFoundError as e:
				print(f"Failed to get config for server \"{server.name}\" with ID [{server.id}].")
				Bot.create_server_config(server)
		print(self.server_info)

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

		server_path = f"servers/{server.id}"
		config_path = f"{server_path}/config.json"
		if os.path.exists(config_path):
			print("\tConfig already exists.")
			return

		if not os.path.isdir(server_path):
			os.makedirs(server_path)
		shutil.copyfile('config_base.json', config_path)

		print("\tSuccessfully created config.")

	
if __name__ == "__main__":
	main()

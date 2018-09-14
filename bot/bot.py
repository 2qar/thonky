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

#TODO: use discord.ext.commands instead of this garbage
from bot.commands.get_info_command import GetInfoCommand
from bot.commands.update_command import UpdateCommand
import bot.commands.ping_command as ping_cmd

class Bot(discord.Client):
	def __init__(self, token, server_info):
			super().__init__()
			#TODO: change from a boolean to checking if the bot is scanning in a server so this doesn't prevent multiple servers from updating at the same time
			self.scanning = False
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
		#self.scheduler.init_schedule_pings(self)

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
			server_path = f"servers/{server.id}"
			config_path = f"{server_path}/config.json"
			try:
				current_info = {}

				server_config = json.load(open(config_path))
				doc_key = server_config['doc_key']
				scraper = SheetScraper(doc_key)
				current_info['scraper'] = scraper
				current_info['players'] = scraper.get_players()
				current_info['week_schedule'] = scraper.get_week_schedule()

				self.server_info[server.id] = current_info
			except FileNotFoundError as e:
				print(f"Failed to get config for server \"{server.name}\" with ID [{server.id}]. Creating config file...")
				if not os.path.exists(server_path):
					os.makedirs(server_path)
				shutil.copyfile('config_base.json', config_path)
				print("\tSuccessfully made a copy of the base config for this server.")
					

		print("Ready! :)")
		
	async def on_message(self, message):
		await self.wait_until_ready()

		if ping_cmd.ping_list:
			ping_cmd.check_to_stop(message)

		if message.content.startswith("!"):
			if message.content.startswith("!get"):
				await GetInfoCommand.invoke(self, message)
			elif message.content.startswith("!update"):
				await UpdateCommand.invoke(self, message.channel)
			elif message.content.startswith("!ping"):
				await ping_cmd.ping(self, message)
	
if __name__ == "__main__":
	main()

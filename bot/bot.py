import discord
import asyncio
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
	def __init__(self, token, scheduler_config):
			super().__init__()
			self.scraper = SheetScraper()
			self.players = self.scraper.get_players()
			self.week_schedule = self.scraper.get_week_schedule()
			self.scheduler = PingScheduler(scheduler_config)
			self.scanning = False
			self.scheduler.init_auto_update(self)
			self.scheduler.init_save_player_data(self)
			self.run(token)
	
	async def on_ready(self):
		playing = discord.Game(name="with spreadsheets", url=sheet_url, type=1)
		await self.change_presence(game=playing)
		self.scheduler.init_schedule_pings(self)
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

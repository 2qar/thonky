import discord
import asyncio

from .sheetbot import SheetScraper
from .formatter import Formatter
from .ping_scheduler import PingScheduler
from .player_saver import PlayerSaver

from bot.commands.get_info_command import GetInfoCommand
from bot.commands.update_command import UpdateCommand

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
		playing = discord.Game(name="with spreadsheets", url=Formatter.sheet_url, type=1)
		await self.change_presence(game=playing)
		self.scheduler.init_schedule_pings(self)
		print("Ready! :)")
		
	async def on_message(self, message):
		await self.wait_until_ready()
		if message.content.startswith("!"):
			if message.content.startswith("!get"):
				await GetInfoCommand.invoke(self, message)
			elif message.content.startswith("!update"):
				await UpdateCommand.invoke(self, message.channel)
	
if __name__ == "__main__":
	main()

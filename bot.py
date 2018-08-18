import discord
import asyncio
import traceback

from players import Player
from sheetbot import SheetScraper
from formatter import Formatter
from timezonehelper import TimezoneHelper
import calendar
import datetime
from pytz import timezone
import pytz
from ping_scheduler import PingScheduler
from player_saver import PlayerSaver

main_token = 'NDc3NjI3MzczMDMwNzM1ODcy.DlDQeg.MRWwrnDCSmfOxsY3mq6TsWkR5sI'
test_token = 'NDY4MDg0NjExOTgxNzcwNzU3.DlDRLg.ymoPR53jRHqujSNGfZ0tBwf4w64'

#TODO: Save player player responses to JSON every Sunday night, make command that gets averages for player responses (ex 60% Yes, 20% Maybe, 20% No)
	#maybe make more commands using this player data
class Bot(discord.Client):
	def __init__(self):
			super().__init__()
			self.scraper = SheetScraper()
			self.players = self.scraper.get_players()
			self.week_schedule = self.scraper.get_week_schedule()
			self.scheduler = PingScheduler()
			self.scanning = False
			self.scheduler.init_auto_update(self)
			self.scheduler.init_schedule_pings(self, self.week_schedule)
			self.scheduler.init_save_player_data(self.scraper)
			self.run(test_token)
	
	async def on_ready(self):
		playing = discord.Game(name="with spreadsheets", url=Formatter.sheet_url, type=1)
		await self.change_presence(game=playing)
		print("Ready! :)")
		
	async def on_message(self, message):
		await self.wait_until_ready()
		if message.content.startswith("!"):
			if message.content.startswith("!get"):
				await self.check_player_command(message)
			elif message.content.startswith("!update"):
				await Bot.update(message.channel)

	#TODO: Add a help message for this command and all of the variants and arguments and shit
	#TODO: Make each command its own class, each command will have an invoke() and a help() method
		#maybe make an abstract command class
	async def check_player_command(self, message):
		content = message.content
		print(content)
		print(content.split())
		day = Bot.get_today_name()
		start = 4
		Formatter.zone = "PDT"

		split_msg = content.split()
		if "tomorrow" in split_msg:
			try:
				day = calendar.day_name[datetime.date.today().weekday() + 1]
			except:
				await self.send_message(message.channel, "It's Sunday silly")
				return

		try:
			tz = TimezoneHelper.get_timezone(split_msg[len(split_msg) - 1])
			del(split_msg[len(split_msg) - 1])
			start_info = TimezoneHelper.get_start_time(tz)
			start = start_info[0]
			Formatter.zone = start_info[1]
			print("Start Time: ", start)
		except:
			print("not doin this shit")
		
		if len(split_msg) == 2:
			given_day = content.split()[1].lower()
			player = self.get_player_by_name(given_day)
			if player != None:
				schedule_embed = Formatter.get_player_on_day(player, day, start)
				await self.send_message(message.channel, embed=schedule_embed)
				return

			try:
				schedule_embed = Formatter.get_hour_schedule(self.players, self.week_schedule, day, given_day, start)
				await self.send_message(message.channel, embed=schedule_embed)
				return
			except:
				print("Attempted to get schedule for day with start time ", given_day)
			if given_day == "today" or given_day == "tomorrow":
				schedule_embed = Formatter.get_day_schedule(self.players, day, start)
				await self.send_message(message.channel, embed=schedule_embed)
				return
			elif given_day == "week":
				await self.send_message(message.channel, embed=Formatter.get_week_activity_schedule(self.week_schedule, start))
				return
			else:
				day = content.split()[1].title()
				if not day in list(calendar.day_name):
					await self.send_message(message.channel, "Invalid day.")
					return
				schedule_embed = Formatter.get_day_schedule(self.players, day, start)
				await self.send_message(message.channel, embed=schedule_embed)
				return
			await self.send_message("Invalid command: no player/day given.")
		elif len(split_msg) == 3:
			player_name = split_msg[1]
			# target could be a day or avg
			target = split_msg[2].lower()
			player = self.get_player_by_name(player_name)
			if player != None:
				if target == "tomorrow" or target == "today":
					schedule_embed = Formatter.get_player_on_day(player, day, start)
					await self.send_message(message.channel, embed=schedule_embed)
					return
				elif target == "avg" or target == "average":
					# get the averages for a player
					pass
				else:
					await self.send_message(message.channel, "Invalid time given.")
			else:
				await self.send_message(message.channel, "Invalid player given.")
		#TODO: Add "!get today at [time]" and "!get tomorrow at [time]"
		elif len(split_msg) == 4:
			# target could be day name or player name
			target = split_msg[1].lower()
			
			decider = split_msg[2].lower()
			# given day could be a day or a time
			given_day = split_msg[3].title()
						
			if decider == "at":
				player = self.get_player_by_name(target)
				if player == None:
					try:
						if target == 'tomorrow':
							await self.send_message(message.channel, embed=Formatter.get_hour_schedule(self.players, self.week_schedule, day, given_day, start))
						else:
							await self.send_message(message.channel, embed=Formatter.get_hour_schedule(self.players, self.week_schedule, target, given_day, start))
					except Exception as e:
						await self.send_message(message.channel, "Invalid time or day. {}".format(e))
						traceback.print_exc()
				else:
						try:
							await self.send_message(message.channel, Formatter.get_player_at_time(player, Bot.get_today_name(), given_day, start))
						except:
							await self.send_message(message.channel, "Invalid time.")
			elif decider == "on":
				try:
					await self.send_message(message.channel, embed=Formatter.get_player_on_day(player, given_day, start))
				except:
					await self.send_message(message.channel, "Invalid time.")
			else:
				await self.send_message(message.channel, "Invalid identifier.")
		elif len(split_msg) == 6:
			player_name = split_msg[1].lower()
			player = self.get_player_by_name(player_name)
			if player == None:
				await self.send_message(message.channel, "Invalid player.")
				return

			time = split_msg[3]
			given_day = split_msg[5].title()

			if not given_day in list(calendar.day_name):
				await self.send_message(message.channel, "Invalid day.")
			else:
				try:
					msg = Formatter.get_player_at_time(player, given_day, time, start)
					await self.send_message(message.channel, msg)
				except:
					await self.send_message(message.channel, "Invalid time.")

	async def post_week_schedule(players, channel):
		embeds = Formatter.get_week_schedule(players)
		for schedule_embed in embeds:
			await self.send_message(channel, embed=schedule_embed)
			await asyncio.sleep(1)

	def get_today_name():
		day_int = datetime.date.today().weekday()
		return calendar.day_name[day_int]

	async def update(self, channel=None):
		should_send_messages = channel != None

		if self.scanning: return

		self.scanning = True
		if should_send_messages: 
			await self.send_message(channel, "Scanning sheet...")

		self.scraper.authenticate()
		self.players = self.scraper.get_players()
		self.week_schedule = self.scraper.get_week_schedule()
		self.scheduler.init_schedule_pings(self, self.week_schedule)

		if should_send_messages: 
			await self.send_message(channel, "Rescanned sheet.")
		self.scanning = False

	def get_player_by_name(self, name):
		for player in self.players.unsorted_list:
			if player.name.lower() == name.lower():
				return player

bot = Bot()

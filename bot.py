import discord
import asyncio
from sheetbot import Player
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

#TODO: Reorganize the project: Bot class should extend Client, some classes like this one should be instanceable, some classes in sheetbot.py should be moved to their own files
#TODO: A command to check the activity schedule (just add a command to the formatter to format the data from scraper.get_week_schedule())
#TODO: Save player player responses to JSON every Sunday night, make command that gets averages for player responses (ex 60% Yes, 20% Maybe, 20% No)
	#maybe make more commands using this player data
class Bot():
	client = discord.Client()
	scraper = SheetScraper()
	players = scraper.get_players()
	week_schedule = scraper.get_week_schedule()
	scheduler = PingScheduler()
	scanning = False
	
	@client.event
	async def on_ready():
		print("Ready! :)")
		playing = discord.Game(name="with spreadsheets", url=Formatter.sheet_url, type=1)
		await Bot.client.change_presence(game=playing)
		Bot.scheduler.init_auto_update(Bot.update)
		Bot.scheduler.init_schedule_pings(Bot.client, Bot.week_schedule)
		Bot.scheduler.init_save_player_data(Bot.scraper)
		
	@client.event
	async def on_message(message):
		if message.content.startswith("!"):
			if message.content.startswith("!get"):
				await Bot.check_player_command(message)
			elif message.content.startswith("!update"):
				await Bot.update(message.channel)

	#TODO: Add a help message for this command and all of the variants and arguments and shit
	async def check_player_command(message):
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
				await Bot.client.send_message(message.channel, "It's Sunday silly")
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
			player = Bot.get_player_by_name(given_day)
			if player != None:
				schedule_embed = Formatter.get_player_on_day(player, day, start)
				await Bot.client.send_message(message.channel, embed=schedule_embed)
				return

			try:
				schedule_embed = Formatter.get_hour_schedule(Bot.players, Bot.week_schedule, day, given_day, start)
				await Bot.client.send_message(message.channel, embed=schedule_embed)
				return
			except:
				print("Attempted to get schedule for day with start time ", given_day)
			if given_day == "today" or given_day == "tomorrow":
				schedule_embed = Formatter.get_day_schedule(Bot.players, day, start)
				await Bot.client.send_message(message.channel, embed=schedule_embed)
				return
			elif given_day == "week":
				await Bot.post_week_schedule(Bot.players, message.channel)
				return
			else:
				day = content.split()[1].title()
				if not day in list(calendar.day_name):
					await Bot.client.send_message(message.channel, "Invalid day.")
					return
				schedule_embed = Formatter.get_day_schedule(Bot.players, day, start)
				await Bot.client.send_message(message.channel, embed=schedule_embed)
				return
			await Bot.client.send_message("Invalid command: no player/day given.")
		elif len(split_msg) == 3:
			player_name = split_msg[1]
			given_day = split_msg[2].lower()
			player = Bot.get_player_by_name(player_name)
			if player != None:
				if given_day == "tomorrow" or given_day == "today":
					schedule_embed = Formatter.get_player_on_day(player, day, start)
					await Bot.client.send_message(message.channel, embed=schedule_embed)
					return
				else:
					await Bot.client.send_message(message.channel, "Invalid time given.")
			else:
				await Bot.client.send_message(message.channel, "Invalid player given.")
		#TODO: Add format "!get friday at 4"
		elif len(split_msg) == 4:
			player_name = split_msg[1].lower()
			player = Bot.get_player_by_name(player_name)
			if player == None:
				await Bot.client.send_message(message.channel, "Invalid player.")
				return

			decider = split_msg[2].lower()
			given_day = split_msg[3].title()
			if not given_day in list(calendar.day_name) and decider == "on":
				await Bot.client.send_message(message.channel, "Invalid day name")
				return
			
			if decider == "at":
				try:
					await Bot.client.send_message(message.channel, Formatter.get_player_at_time(player, Bot.get_today_name(), given_day, start))
				except:
					await Bot.client.send_message(message.channel, "Invalid time.")
			elif decider == "on":
				try:
					await Bot.client.send_message(message.channel, embed=Formatter.get_player_on_day(player, given_day, start))
				except:
					await Bot.client.send_message(message.channel, "Invalid time.")
			else:
				await Bot.client.send_message(message.channel, "Invalid identifier.")
		elif len(split_msg) == 6:
			player_name = split_msg[1].lower()
			player = Bot.get_player_by_name(player_name)
			if player == None:
				await Bot.client.send_message(message.channel, "Invalid player.")
				return

			time = split_msg[3]
			given_day = split_msg[5].title()

			if not given_day in list(calendar.day_name):
				await Bot.client.send_message(message.channel, "Invalid day.")
			else:
				try:
					msg = Formatter.get_player_at_time(player, given_day, time, start)
					await Bot.client.send_message(message.channel, msg)
				except:
					await Bot.client.send_message(message.channel, "Invalid time.")

	async def post_week_schedule(players, channel):
		embeds = Formatter.get_week_schedule(players)
		for schedule_embed in embeds:
			await Bot.client.send_message(channel, embed=schedule_embed)
			await asyncio.sleep(1)

	def get_today_name():
		day_int = datetime.date.today().weekday()
		return calendar.day_name[day_int]

	async def update(channel=None):
		should_send_messages = channel != None

		if Bot.scanning: return

		Bot.scanning = True
		if should_send_messages: 
			await Bot.client.send_message(channel, "Scanning sheet...")
		Bot.players = Bot.scraper.get_players()
		Bot.week_schedule = Bot.scraper.get_week_schedule()
		Bot.scheduler.init_schedule_pings(Bot.client, Bot.week_schedule)
		if should_send_messages: 
			await Bot.client.send_message(channel, "Rescanned sheet.")
		Bot.scanning = False

	def get_player_by_name(name):
		for player in Bot.players:
			if player.name.lower() == name.lower():
				return player

Bot.client.run(main_token)

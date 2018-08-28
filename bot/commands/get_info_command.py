import asyncio
import calendar
import datetime
import pytz
from pytz import timezone
import random

from bot.timezonehelper import TimezoneHelper
from bot.formatter import Formatter
from bot.odscraper import get_other_team_info

#TODO: Make help method
class GetInfoCommand():
	async def invoke(bot, message):
		content = message.content

		print(content)
		print(content.split())

		if content.lower() == '!get superior hog':
			superior_hog = ['ADS', 'Tydra'][random.randrange(0, 2)]
			await bot.send_message(message.channel, superior_hog)
			return

		# get the name of today
		day = calendar.day_name[datetime.date.today().weekday()]
		start = 4
		Formatter.zone = "PDT"

		split_msg = content.split()
		if "tomorrow" in split_msg:
			try:
				day = calendar.day_name[datetime.date.today().weekday() + 1]
			except:
				await bot.send_message(message.channel, "It's Sunday silly")
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
			player = GetInfoCommand.get_player_by_name(bot, given_day)
			if player != None:
				schedule_embed = Formatter.get_player_on_day(player, day, start)
				await bot.send_message(message.channel, embed=schedule_embed)
				return

			try:
				schedule_embed = Formatter.get_hour_schedule(bot.players, bot.week_schedule, day, given_day, start)
				await bot.send_message(message.channel, embed=schedule_embed)
				return
			except:
				print("Attempted to get schedule for day with start time ", given_day)
			if given_day == "today" or given_day == "tomorrow":
				schedule_embed = Formatter.get_day_schedule(bot.players, day, start)
				await bot.send_message(message.channel, embed=schedule_embed)
				return
			elif given_day == "week":
				await bot.send_message(message.channel, embed=Formatter.get_week_activity_schedule(bot.week_schedule, start))
				return
			else:
				day = content.split()[1].title()
				if not day in list(calendar.day_name):
					await bot.send_message(message.channel, "Invalid day.")
					return
				schedule_embed = Formatter.get_day_schedule(bot.players, day, start)
				await bot.send_message(message.channel, embed=schedule_embed)
				return
			await bot.send_message("Invalid command: no player/day given.")
		elif len(split_msg) == 3:
			player_name = split_msg[1]
			# target could be a day or avg
			target = split_msg[2].lower()
			player = GetInfoCommand.get_player_by_name(bot, player_name)
			if player != None:
				if target == "tomorrow" or target == "today":
					schedule_embed = Formatter.get_player_on_day(player, day, start)
					await bot.send_message(message.channel, embed=schedule_embed)
					return
				elif target == "avg" or target == "average":
					average_embed = Formatter.get_player_averages(player.name)
					await bot.send_message(message.channel, embed=average_embed)
				else:
					await bot.send_message(message.channel, "Invalid time given.")
			elif player_name == "od":
				try:
					wait_message = await bot.send_message(message.channel, "Grabbing match info...")
					team_info = await get_other_team_info(target)
					od_embed = Formatter.get_enemy_team_info(target, team_info)
					await bot.delete_message(wait_message)
					await bot.send_message(message.channel, embed=od_embed)
				except:
					await bot.send_message(message.channel, "Invalid round given.")
			else:
				await bot.send_message(message.channel, "Invalid player given.")
		#TODO: Add "!get today at [time]" and "!get tomorrow at [time]"
		elif len(split_msg) == 4:
			# target could be day name or player name
			target = split_msg[1].lower()
			
			decider = split_msg[2].lower()
			# given day could be a day or a time
			given_day = split_msg[3].title()
						
			if decider == "at":
				player = GetInfoCommand.get_player_by_name(bot, target)
				if player == None:
					try:
						if target == 'tomorrow':
							await bot.send_message(message.channel, embed=Formatter.get_hour_schedule(bot.players, bot.week_schedule, day, given_day, start))
						else:
							await bot.send_message(message.channel, embed=Formatter.get_hour_schedule(bot.players, bot.week_schedule, target, given_day, start))
					except:
						await bot.send_message(message.channel, "Invalid time or day. {}".format(e))
				else:
						try:
							await bot.send_message(message.channel, Formatter.get_player_at_time(player, Bot.get_today_name(), given_day, start))
						except:
							await bot.send_message(message.channel, "Invalid time.")
			elif decider == "on":
				try:
					await bot.send_message(message.channel, embed=Formatter.get_player_on_day(player, given_day, start))
				except:
					await bot.send_message(message.channel, "Invalid time.")
			else:
				await bot.send_message(message.channel, "Invalid identifier.")
		elif len(split_msg) == 6:
			player_name = split_msg[1].lower()
			player = GetInfoCommand.get_player_by_name(bot, player_name)
			if player == None:
				await bot.send_message(message.channel, "Invalid player.")
				return

			time = split_msg[3]
			given_day = split_msg[5].title()

			if not given_day in list(calendar.day_name):
				await bot.send_message(message.channel, "Invalid day.")
			else:
				try:
					msg = Formatter.get_player_at_time(player, given_day, time, start)
					await bot.send_message(message.channel, msg)
				except:
					await bot.send_message(message.channel, "Invalid time.")

	async def help(bot, channel):
		pass

	def get_player_by_name(bot, name):
		for player in bot.players.unsorted_list:
			if player.name.lower() == name.lower():
				return player

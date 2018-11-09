import asyncio
import calendar
import datetime
import pytz
from pytz import timezone
import random

from bot.timezonehelper import TimezoneHelper
from bot.formatter import Formatter
from bot.dbhandler import DBHandler


class GetInfoCommand():
	async def invoke(bot, message):
		def get_player_by_name(server_info, name):
			for player in server_info.players.unsorted_list:
				if player.name.lower() == name.lower():
					return player

		content = message.content
		channel = message.channel
		server_info = bot.server_info
		server_id = message.server.id

		try:
			server_info = server_info[server_id]
		except:
			await bot.send_message(channel, "ERROR: No doc key provided for this server.")
			return

		print(content)
		print(content.split())

		if content.lower() == '!get superior hog':
			superior_hog = ['ADS', 'Tydra'][random.randrange(0, 2)]
			await bot.send_message(channel, superior_hog)
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
				await bot.send_message(channel, "It's Sunday silly")
				return

		try:
			tz = TimezoneHelper.get_timezone(split_msg[-1])
			del(split_msg[-1])
			start_info = TimezoneHelper.get_start_time
			start = start_info[0]
			Formatter.zone = start_info[1]
			print("Start Time: ", start)
		except:
			print("not doin this shit")
		
		if len(split_msg) == 2:
			given_day = content.split()[1].lower()
			player = get_player_by_name(server_info, given_day)
			if player:
				schedule_embed = Formatter.get_player_on_day(server_id, player, day, start)
				await bot.send_message(channel, embed=schedule_embed)
				return

			try:
				schedule_embed = Formatter.get_hour_schedule(server_id, server_info, day, given_day, start)
				await bot.send_message(channel, embed=schedule_embed)
				return
			except:
				print("Attempted to get schedule for day with start time ", given_day)

			if given_day in ['today', 'tomorrow']:
				schedule_embed = Formatter.get_day_schedule(server_id, server_info.players, day, start)
				await bot.send_message(channel, embed=schedule_embed)
				return
			elif given_day == "week":
				await bot.send_message(channel, embed=Formatter.get_week_activity_schedule(server_id, server_info.week_schedule, start))
				return
			else:
				day = content.split()[1].title()
				if not day in list(calendar.day_name):
					await bot.send_message(channel, "Invalid day.")
					return
				schedule_embed = Formatter.get_day_schedule(server_id, server_info.players, day, start)
				await bot.send_message(channel, embed=schedule_embed)
				return
			await bot.send_message("Invalid command: no player/day given.")
		elif len(split_msg) == 3:
			player_name = split_msg[1]
			# target could be a day or avg
			target = split_msg[2].lower()
			player = get_player_by_name(server_info, player_name)
			if player != None:
				if target in ['today', 'tomorrow']:
					schedule_embed = Formatter.get_player_on_day(server_id, player, day, start)
					await bot.send_message(channel, embed=schedule_embed)
				elif target in ['avg', 'average']:
					average_embed = Formatter.get_player_averages(server_id, player.name)
					if average_embed:
						await bot.send_message(channel, embed=average_embed)
					else:
						await bot.send_message(channel, f"ERROR: No data for {player.name}.")
				else:
					await bot.send_message(channel, "Invalid time given.")
			elif player_name == "od":
				try:
					od_round = target
					wait_message = await bot.send_message(channel, "Grabbing match info...")

					with DBHandler() as handler:
						team_id = handler.get_server_config(server_id)['team_id']

					if not team_id:
						await bot.send_message(channel, "ERROR: No team id given. Run '!set_team <link to battlefy team>'.")
						return

					team_info = await get_other_team_info(od_round, team_id)
					od_embed = Formatter.get_enemy_team_info(od_round, team_info)

					await bot.delete_message(wait_message)
					await bot.send_message(channel, embed=od_embed)
				except:
					await bot.send_message(channel, "Invalid round given.")
			else:
				await bot.send_message(channel, "Invalid player given.")
		elif len(split_msg) == 4:
			# target could be day name or player name
			target = split_msg[1].lower()
			
			decider = split_msg[2].lower()
			# given day could be a day or a time
			given_day = split_msg[3].title()

			player = get_player_by_name(server_info, target)
			if decider == "at":
				if not player:
					try:
						target_day = day if target in ['today', 'tomorrow'] else target
						await bot.send_message(channel, embed=Formatter.get_hour_schedule(server_id, server_info, target_day, given_day, start))
					except Exception as e:
						await bot.send_message(channel, f"Invalid time or day. {e}")
				else:
						try:
							await bot.send_message(channel, Formatter.get_player_at_time(player, day, given_day, start))
						except:
							await bot.send_message(channel, "Invalid time.")
			elif decider == "on":
				try:
					await bot.send_message(channel, embed=Formatter.get_player_on_day(server_id, player, given_day, start))
				except:
					await bot.send_message(channel, "Invalid day.")
			else:
				await bot.send_message(channel, "Invalid identifier.")
		elif len(split_msg) == 6:
			player_name = split_msg[1].lower()
			player = get_player_by_name(server_info, player_name)
			if player == None:
				await bot.send_message(channel, "Invalid player.")
				return

			time = split_msg[3]
			given_day = split_msg[5].title()

			if not given_day in list(calendar.day_name):
				await bot.send_message(channel, "Invalid day.")
			else:
				try:
					msg = Formatter.get_player_at_time(player, given_day, time, start)
					await bot.send_message(channel, msg)
				except:
					await bot.send_message(channel, "Invalid time.")

	async def help(bot, channel):
		pass

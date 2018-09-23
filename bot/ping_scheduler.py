from apscheduler.schedulers.asyncio import AsyncIOScheduler
import datetime
import calendar
import yaml
import json

from .formatter import Formatter
from .player_saver import PlayerSaver
from .dbhandler import DBHandler
#from bot.commands.update_command.UpdateCommand import bulk_update

class PingScheduler():
	def __init__(self, server_id, config, server_info):
		self.server_id = server_id
		self.config = config
		self.server_info = server_info
		self.scheduler = AsyncIOScheduler()
		self.scheduler.start()
		self.save_day_num = list(calendar.day_name).index(self.config['save_config']['save_day'].title())

	def init_scheduler(self, bot, update_command):
		self.init_save_player_data()
		self.init_auto_update(bot, update_command)
		self.init_schedule_pings(bot)

	def init_save_player_data(self, save_day=None):
		save_time = self.config['save_config']['save_time']
		scraper = self.server_info.scraper
		players = self.server_info.players
		week_schedule = self.server_info.week_schedule

		# gets save day first time this method is called or gets next save day from previous save day given
		if save_day == None:
			today = datetime.date.today()
			monday = today - datetime.timedelta(days=today.weekday())
			save_day = monday + datetime.timedelta(days=self.save_day_num)
		else:
			save_day += datetime.timedelta(days=self.save_day_num + 1)

		today = datetime.datetime.today()
		automated_save_missed = today.weekday() == self.save_day_num and today.hour >= save_time
		run_time = None
		save_time_as_date = datetime.time(save_time)
		if automated_save_missed:
			PlayerSaver.save_players(self.server_id, players, week_schedule)
			next_save_day = today + datetime.timedelta(days=self.save_day_num)
			run_time = datetime.datetime.combine(next_save_day, save_time_as_date)
		else:
			run_time = datetime.datetime.combine(save_day, save_time_as_date)

		self.scheduler.add_job(PlayerSaver.save_players, 'date', run_date=run_time, args=[self.server_id, players, week_schedule])
		self.scheduler.add_job(self.init_save_player_data, 'date', run_date=run_time, args=[save_day])
		self.scheduler.print_jobs()

	def init_auto_update(self, bot, update_command):
		update_interval = self.config['intervals']['update_interval']
		self.scheduler.add_job(update_command, 'interval', minutes=update_interval, args=[bot, self.server_id], id="update_schedule")
		#self.scheduler.add_job(UpdateCommand.invoke, 'interval', minutes=update_interval, args=[bot], id="update_schedule")
	
	def init_schedule_pings(self, bot):
		channel = None
		with DBHandler() as handler:
			config = handler.get_server_config(self.server_id)
			announce_channel = config['announce_channel']
			role_mention = config['role_mention']

		try:
			channel = bot.get_server(self.server_id).get_channel(announce_channel)
		except Exception as e:
			print("couldn't grab server to ping people in, probably using wrong token or this function is being called before the bot is ready: ", e)
			return

		# get the date of the first day of this week
		week_day = datetime.date.today().weekday()
		today = datetime.datetime.today()
		start_date = today - datetime.timedelta(days=week_day)

		days = self.server_info.week_schedule.days
		for day_index in range(0, len(days)):
			# don't add pings to the scheduler if they're in the past
			if day_index >= week_day:
				date = (start_date + datetime.timedelta(days=day_index)).date()
				day = days[day_index]

				# schedule a ping at 9 AM every day sending the schedule for the day, but only if there's something planned
				day_not_free = False
				for activity in day.activities:
					if activity != "Free" and activity != "TBD":
						day_not_free = True
						break
				if day_not_free:
					morning_runtime = datetime.datetime.combine(date, datetime.time(9))
					morning_ping_id = day.name + "_morning_ping"
					embed = Formatter.get_day_schedule(self.server_info.players, day.name, 4)
					self.scheduler.add_job(bot.send_message, 'date', run_date=morning_runtime, args=[channel], kwargs={'embed': embed}, id=morning_ping_id, replace_existing=True)

				# schedule pings before the first activity of the day
				for activity_time in range(0, 6):
					# 16 = 4 PM PST
					time = activity_time + 16
					activity = day.activities[activity_time]
					if not activity in self.config['remind_config']['non_reminder_activities']:
						# schedule pings 15 and 5 minutes before first activity of day
						for interval in self.config['intervals']['remind_intervals']:
							run_time = datetime.datetime.combine(date, datetime.time(time)) - datetime.timedelta(minutes=interval)
							ping_string = f"{role_mention} {activity} in {interval} minutes"
							id_str = day.get_formatted_name() + " " + str(time) + " " + str(interval)
							self.scheduler.add_job(bot.send_message, 'date', run_date=run_time, args=[channel, ping_string], id=id_str, replace_existing=True)
						break

				# open division pings
				'''
				is_weekend = day_index >= 5
				if is_weekend:
					ping_string = f"{role_mention} Start warming up now. Scrim in 30 minutes. Game in 1 hour 30 minutes"
					# run at 10:30 AM
					run_time = datetime.datetime.combine(date, datetime.time(10, 30))
					id_str = day.get_formatted_name() + "_open_division"
					self.scheduler.add_job(bot.send_message, 'date', run_date=run_time, args=[channel, ping_string], id=id_str, replace_existing=True)
				'''

		self.scheduler.print_jobs()

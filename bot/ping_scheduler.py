from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.memory import MemoryJobStore
import datetime
import calendar
import yaml

from .formatter import Formatter
from .player_saver import PlayerSaver
from .dbhandler import DBHandler

class PingScheduler(AsyncIOScheduler):
	def __init__(self, server_id, server_info):
		super().__init__()
		self.start()
		self.add_jobstore(MemoryJobStore(), alias='pings')

		self.server_id = server_id
		with open('config.yaml') as file:
			self.config = [doc for doc in yaml.safe_load_all(file)][1]
		self.server_info = server_info
		self.save_day_num = list(calendar.day_name).index(self.config['save_config']['save_day'].title())

	def init_scheduler(self, bot, update_command):
		#TODO: Load config once and pass it to the 3 methods below
		#with DBHandler() as handler:
			#self.server_info(

		self.init_save_player_data()
		self.init_auto_update(bot, update_command)
		self.init_schedule_pings(bot)
		self.print_jobs()

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

		self.add_job(PlayerSaver.save_players, 'date', run_date=run_time, args=[self.server_id, players, week_schedule])
		self.add_job(self.init_save_player_data, 'date', run_date=run_time, args=[save_day])

	# TODO: Get rid of this in favor of an event handler on the spreadsheet that triggers the bot to update
	def init_auto_update(self, bot, update_command):
		update_interval = self.config['intervals']['update_interval']
		self.add_job(update_command, 'interval', minutes=update_interval, args=[bot, self.server_id], id="update_schedule")
	
	def init_schedule_pings(self, bot):
		channel = None
		with DBHandler() as handler:
			config = handler.get_server_config(self.server_id)
			announce_channel = config['announce_channel']
			role_mention = config['role_mention']
			remind_activities = [activity.lower() for activity in config['remind_activities']]
			remind_intervals = config['remind_intervals']

		try:
			channel = bot.get_server(self.server_id).get_channel(announce_channel)
		except Exception as e:
			print("couldn't grab server to ping people in, probably using wrong token or this function is being called before the bot is ready: ", e)
			return

		today = datetime.date.today().weekday()
		days = self.server_info.week_schedule.days
		start_date = days[0].as_date()

		for day_index in range(0, len(days)):
			# don't add pings to the scheduler if they're in the past
			if day_index >= today:
				date = start_date + datetime.timedelta(days=day_index)
				day = days[day_index]

				first_activity = day.first_activity(remind_activities)
				if first_activity != -1:
					# post the schedule at 9 AM 
					morning_runtime = datetime.datetime.combine(date, datetime.time(9))
					morning_ping_id = day.name + "_morning_ping"
					embed = Formatter.get_day_schedule(self.server_id, self.server_info.players, day.name, 4)
					self.add_job(bot.send_message, 'date', run_date=morning_runtime, args=[channel], kwargs={'embed': embed}, id=morning_ping_id, replace_existing=True, jobstore='pings')

					activity = day.activities[first_activity]
					activity_time = datetime.datetime.combine(date, datetime.time(16 + first_activity))
					for interval in remind_intervals:
						run_time = activity_time - datetime.timedelta(minutes=interval)
						message = f"{role_mention} {activity} in {interval} minutes"
						ping_id = f"{day.get_formatted_name()} {interval} min reminder"
						self.add_job(bot.send_message, 'date', run_date=run_time, args=[channel, message], id=ping_id, replace_existing=True, jobstore='pings')

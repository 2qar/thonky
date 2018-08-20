from apscheduler.schedulers.asyncio import AsyncIOScheduler
import datetime
from formatter import Formatter
from player_saver import PlayerSaver

class PingScheduler():
	server = '438922759372800000'
	announce_channel = '445735181295550467'
	general = '438922759372800002'

	main_roster_mention = '<@&445734608135258141>'

	remind_intervals = [15, 5]
	update_interval = 30
	player_data_save_time = 10 # 24 hr time on Sunday each week

	def __init__(self):
		self.scheduler = AsyncIOScheduler()
		self.scheduler.start()

	def init_save_player_data(self, bot, sunday=None):
		# gets Sunday first time this method is called or gets next Sunday from previous Sunday given
		if sunday == None:
			today = datetime.date.today()
			beginning_of_week = today - datetime.timedelta(days=today.weekday())
			sunday = beginning_of_week + datetime.timedelta(days=6)
		else:
			sunday += datetime.timedelta(days=7)

		today = datetime.datetime.today()
		automated_save_missed = today.weekday() == 6 and today.hour >= PingScheduler.player_data_save_time
		run_time = None
		save_time_as_date = datetime.time(PingScheduler.player_data_save_time)
		if automated_save_missed:
			PlayerSaver.save_players(bot.players, bot.week_schedule)
			next_sunday = today + datetime.timedelta(days=7)
			run_time = datetime.datetime.combine(next_sunday, save_time_as_date)
		else:
			run_time = datetime.datetime.combine(sunday, save_time_as_date)

		self.scheduler.add_job(PlayerSaver.save_players, 'date', run_date=run_time, args=[bot.players, bot.week_schedule])
		self.scheduler.add_job(self.init_save_player_data, 'date', run_date=run_time, args=[bot.scraper, sunday])

	def init_auto_update(self, bot):
		self.scheduler.add_job(bot.update, 'interval', minutes=PingScheduler.update_interval, id="update_schedule")
	
	def init_schedule_pings(self, bot):
		channel = None
		try:
			channel = bot.get_server(PingScheduler.server).get_channel(PingScheduler.announce_channel)
		except Exception as e:
			print("couldn't grab server to ping people in, probably using wrong token or this function is being called before the bot is ready: ", e)
			return

		# get the date of the first day of this week
		week_day = datetime.date.today().weekday()
		today = datetime.datetime.today()
		start_date = today - datetime.timedelta(days=week_day)

		days = bot.week_schedule.days
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
					embed = Formatter.get_day_schedule(bot.players, day.name, 4)
					self.scheduler.add_job(bot.send_message, 'date', run_date=morning_runtime, args=[channel], kwargs={'embed': embed}, id=morning_ping_id, replace_existing=True)

				# schedule pings before the first activity of the day
				for activity_time in range(0, 6):
					# 16 = 4 PM PST
					time = activity_time + 16
					activity = day.activities[activity_time]
					if activity != "Free" and activity != "TBD":
						# schedule pings 15 and 5 minutes before first activity of day
						for interval in PingScheduler.remind_intervals:
							run_time = datetime.datetime.combine(date, datetime.time(time)) - datetime.timedelta(minutes=interval)
							ping_string = "{0} {1} in {2} minutes".format(PingScheduler.main_roster_mention, activity, interval)
							id_str = day.get_formatted_name() + " " + str(time) + " " + str(interval)
							self.scheduler.add_job(bot.send_message, 'date', run_date=run_time, args=[channel, ping_string], id=id_str, replace_existing=True)
						break

				# open division pings
				is_weekend = day_index >= 5
				if is_weekend:
					ping_string = "{} Start warming up now. Scrim in 30 minutes. Game in 1 hour 30 minutes".format(PingScheduler.main_roster_mention)
					# run at 10:30 AM
					run_time = datetime.datetime.combine(date, datetime.time(10, 30))
					id_str = day.get_formatted_name() + "_open_division"
					self.scheduler.add_job(bot.send_message, 'date', run_date=run_time, args=[channel, ping_string], id=id_str, replace_existing=True)

		self.scheduler.print_jobs()

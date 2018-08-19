from apscheduler.schedulers.asyncio import AsyncIOScheduler
import datetime
from formatter import Formatter

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

	def init_save_player_data(self, sheetscraper):
		today = datetime.date.today()
		beginning_of_week = today - datetime.timedelta(days=today.weekday())
		sunday = beginning_of_week + datetime.timedelta(days=6)
		grab_player_time = datetime.datetime.combine(sunday, datetime.time(PingScheduler.player_data_save_time))
		self.scheduler.add_job(sheetscraper.get_players, 'date', run_date=grab_player_time)

	def init_auto_update(self, bot):
		self.scheduler.add_job(bot.update, 'interval', minutes=PingScheduler.update_interval, id="update_schedule")
	
	def init_schedule_pings(self, bot):
		channel = None
		try:
			channel = bot.get_server(PingScheduler.server).get_channel(PingScheduler.announce_channel)
		except:
			print("couldn't grab server to ping people in, probably using wrong token or this function is being called before the bot is ready")
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

		self.scheduler.print_jobs()

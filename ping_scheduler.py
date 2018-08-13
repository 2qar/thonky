from apscheduler.schedulers.asyncio import AsyncIOScheduler
import datetime

#TODO: schedule auto-updating of the spreadsheet so nobody has to do that
class PingScheduler():
	server = '438922759372800000'
	announce_channel = '445735181295550467'
	general = '438922759372800002'
	def __init__(self):
		self.scheduler = AsyncIOScheduler()
		self.scheduler.start()

	def init_auto_update(self, update):
		self.scheduler.add_job(update, 'interval', hours=1, id="update_schedule")
	
	def init_schedule_pings(self, bot_client, week_schedule):
		try:
			channel = bot_client.get_server(PingScheduler.server).get_channel(PingScheduler.announce_channel)
		except:
			print("couldn't grab server to ping people in, probably using wrong token")
			return

		# get the date of the first day of this week
		week_day = datetime.date.today().weekday()
		today = datetime.datetime.today()
		start_date = today - datetime.timedelta(days=week_day)

		days = week_schedule.days
		for day_index in range(0, len(days)):
			# don't add pings to the scheduler if they're in the past
			if day_index >= week_day:
				date = (start_date + datetime.timedelta(days=day_index)).date()
				day = days[day_index]
				print("{0} {1}".format(day, date))
				for i in range(0, 6):
					time = i + 16
					activity = day.activities[i]
					if activity != "Free" and activity != "TBD":
						run_time = datetime.datetime.combine(date, datetime.time(time)) - datetime.timedelta(minutes=30)
						ping_string = "@everyone {0} in 30 minutes".format(activity)
						id_str = day.get_formatted_name() + " " + str(time)
						self.scheduler.add_job(bot_client.send_message, 'date', run_date=run_time, args=[channel, ping_string], id=id_str, replace_existing=True)
						break

		self.scheduler.print_jobs()

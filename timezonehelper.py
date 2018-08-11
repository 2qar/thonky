from pytz import timezone
import datetime
import calendar

class TimezoneHelper():
	def get_timezone(timezone_str):
		timezone_str = timezone_str.upper()
		pacific_zones = ["PT", "PST", "PDT"]
		mountain_zones = ["MT", "MST", "MDT"]
		central_zones = ["CT", "CST", "CDT"]
		eastern_zones = ["ET", "EST", "EDT"]

		zone = ""
		if timezone_str in pacific_zones:
			zone = "US/Pacific"
		elif timezone_str in mountain_zones:
			zone = "US/Mountain"
		elif timezone_str in central_zones:
			zone = "US/Central"
		elif timezone_str in eastern_zones:
			zone = "US/Eastern"
		return timezone(zone)

	def get_start_time(tz):
		utc_now = datetime.datetime.utcnow()
		# starting time = 4 PM PDT
		utc_start = datetime.datetime(utc_now.year, utc_now.month, utc_now.day, 23, 0, 0)
		tz_start = tz.localize(utc_start)
		hour = tz_start.hour + (tz_start.utcoffset().total_seconds() / 3600)
		hour %= 12
		hour = int(hour)
		return hour

	def get_today_name(tz):
		day_int = tz.localize(datetime.datetime.utcnow()).weekday()
		return calendar.day_name[day_int]

print(TimezoneHelper.get_start_time(timezone("US/Pacific")))

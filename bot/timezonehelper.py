from pytz import timezone
import datetime
from collections import namedtuple

Zone = namedtuple('Zone', ('abbreviations', 'pytz_zone'))
pacific_zones = Zone(["PT", "PST", "PDT"], 'US/Pacific')
mountain_zones = Zone(["MT", "MST", "MDT"], 'US/Mountain')
central_zones = Zone(["CT", "CST", "CDT"], 'US/Central')
eastern_zones = Zone(["ET", "EST", "EDT"], 'US/Eastern')
zones = [pacific_zones, mountain_zones, central_zones, eastern_zones]


class TimezoneHelper():
    def get_timezone(tz: str):
        tz = tz.upper()

        for zone in zones:
            if tz in zone.abbreviations:
                return timezone(zone.pytz_zone)

    def get_start_time(tz: str):
        timezone = TimezoneHelper.get_timezone(tz)
        if timezone:
            return TimezoneHelper.get_start_time_info(timezone)[0]

    def get_start_time_info(tz):
        utc_now = datetime.datetime.utcnow()
        # starting time = 4 PM PDT
        utc_start = datetime.datetime(utc_now.year, utc_now.month, utc_now.day, 23, 0, 0)
        tz_start = tz.localize(utc_start)
        hour = tz_start.hour + (tz_start.utcoffset().total_seconds() / 3600)
        hour %= 12
        hour = int(hour)
        timezone = tz_start.tzinfo.tzname(tz_start)
        return [hour, timezone]

from pytz import timezone
from pytz import utc
import datetime
from collections import namedtuple

Zone = namedtuple('Zone', ('abbreviations', 'pytz_zone'))
pacific_zones = Zone(["PT", "PST", "PDT"], 'US/Pacific')
mountain_zones = Zone(["MT", "MST", "MDT"], 'US/Mountain')
central_zones = Zone(["CT", "CST", "CDT"], 'US/Central')
eastern_zones = Zone(["ET", "EST", "EDT"], 'US/Eastern')
zones = [pacific_zones, mountain_zones, central_zones, eastern_zones]


def get_timezone(tz: str):
    """ Get a pytz.timezone object from a timezone abbreviation. """
    tz = tz.upper()

    for zone in zones:
        if tz in zone.abbreviations:
            return timezone(zone.pytz_zone)


def get_start_time(tz: str):
    zone = get_timezone(tz)
    if zone:
        utc_now = datetime.datetime.utcnow()
        utc_start = datetime.datetime(utc_now.year, utc_now.month, utc_now.day, 23, 0, 0, tzinfo=utc)
        localized = utc_start.astimezone(zone)
        if localized:
            if not is_dst(localized):
                localized += datetime.timedelta(hours=1)
            return localized.hour % 12


def is_dst(date: datetime):
    return bool(date.dst())

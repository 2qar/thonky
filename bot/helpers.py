from datetime import datetime, timedelta


def strip_microseconds(dt: datetime) -> datetime:
    return dt - timedelta(microseconds=dt.microsecond)


def stripped_utcnow() -> datetime:
    return strip_microseconds(datetime.utcnow())


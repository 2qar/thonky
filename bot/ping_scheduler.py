from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import datetime
import calendar
import json
from typing import Callable

from .server_info import BaseInfo
from .formatter import get_formatter, Formatter
from .schedules import DaySchedule


# TODO: Eventually rewrite the whole jobstore thing
#       Instead of each ServerInfo having it's own maintenance and pings jobstore,
#       have one maintenance and pings jobstore on the scheduler and use functions to manage jobs from multiple servers
class PingScheduler(AsyncIOScheduler):
    def __init__(self):
        super().__init__()
        self.start()
        self.info = None

        with open('config.json') as file:
            self.config = json.load(file)
        self.save_day_num = list(calendar.day_name).index(self.config['save_day'].title())
        self.save_time = self.config['save_time']

    @property
    def info_id(self):
        return self.info.get_id()

    def has_info_jobstores(self, info: BaseInfo):
        try:
            return bool(self._lookup_jobstore(f"{info.get_id()}_pings"))
        except KeyError:
            return False

    def setup_guild(self, info: BaseInfo):
        for key, jobstore in info.jobstores.items():
            self.add_jobstore(jobstore, alias=f"{info.get_id()}_{key}")

        self.info = info
        self.init_save_player_data()
        self.init_auto_update(info)
        channel = info.get_ping_channel()
        if channel:
            self.init_schedule_pings(channel, info)

    def add_guild_job(self, func: Callable, run_date: datetime, jobstore: str, **kwargs):
        self.add_job(func, 'date', run_date=run_date, jobstore=f"{self.info_id}_{jobstore}", **kwargs)

    def init_save_player_data(self):
        today = datetime.datetime.today()
        if today.weekday() > self.save_day_num or \
                today.weekday() == self.save_day_num and today.time().hour >= self.save_time:
            self.info.save_players()

        self.add_job(self.info.save_players,
                     trigger=CronTrigger(day_of_week=self.save_day_num, hour=self.save_time),
                     jobstore=f"{self.info_id}_maintenance")

    def init_auto_update(self, server_info):
        update_interval = self.config['update_interval']
        self.add_job(server_info.update, 'interval', minutes=update_interval, id="update_schedule",
                     jobstore=f"{self.info_id}_maintenance")

    def _get_run_time(self, time_offset: int):
        """ Run time at 4 PST plus offset """
        return datetime.time(16 + time_offset)

    def _add_ping(self, date, channel, msg_start, time_offset, search_list, intervals):
        item = search_list[time_offset]
        time = datetime.datetime.combine(date, self._get_run_time(time_offset))
        for interval in intervals:
            run_time = time - datetime.timedelta(minutes=interval)
            msg_start = '' if msg_start == 'None' else msg_start
            message = f"{msg_start} {item} in {interval} minutes"
            day_name = Formatter.day_name(date.weekday())
            ping_id = f"{day_name} {interval}"
            self.add_guild_job(
                channel.send,
                run_time,
                "pings",
                name=item,
                args=[message],
                id=ping_id,
                replace_existing=True
            )

    def _add_activity_ping(self, day: DaySchedule, channel, config):
        self._add_ping(day.as_date(), channel, config['role_mention'], day.first_activity(config['remind_activities']),
                       day.activities, config['remind_intervals'])

    def _add_morning_schedule_post(self, day: DaySchedule, info: BaseInfo, channel):
        date = day.as_date()
        morning_runtime = datetime.datetime.combine(date, datetime.time(9))
        morning_ping_id = day.name + "_morning_ping"
        embed = get_formatter(info, 'PST').get_day_schedule(
            info.players,
            date.weekday()
        )
        self.add_guild_job(
            channel.send,
            morning_runtime,
            "pings",
            kwargs={'embed': embed},
            id=morning_ping_id,
            replace_existing=True
        )

    def init_schedule_pings(self, channel, info: BaseInfo):
        config = info.config

        schedule = info.week_schedule
        today = schedule.today.as_date()

        for day_index, day in enumerate(schedule[today.weekday()::]):
            first_activity = day.first_activity(config['remind_activities'])
            if first_activity != -1:
                self._add_morning_schedule_post(day, info, channel)
                self._add_activity_ping(day, channel, config)

        self.print_jobs(jobstore=f"{info.get_id()}_pings")

    def update_schedule_pings(self, week_schedule, info: BaseInfo):
        today = datetime.date.today().weekday()
        for day in week_schedule[today:]:
            self.update_day_pings(day, info)

    def update_day_pings(self, day: DaySchedule, info: BaseInfo):
        print("Updating pings on ", day)
        pingstore = f"{info.get_id()}_pings"
        remind_activities = info.config['remind_activities']

        today = day.as_date().weekday()
        jobs = [job for job in self.get_jobs(jobstore=pingstore) if job.next_run_time.date().weekday() == today]
        first_activity = day.first_activity(remind_activities)

        if first_activity == -1:
            for job in jobs:
                self.remove_job(job.id, jobstore=pingstore)
        else:
            channel = info.get_ping_channel()
            self._add_morning_schedule_post(day, info, channel)
            self._add_activity_ping(day, channel, info.config)
        print("Updated jobs for ", pingstore)
        self.print_jobs(jobstore=pingstore)

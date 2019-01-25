from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import datetime
import calendar
import json
from typing import Callable

from .server_info import BaseInfo
from .formatter import get_formatter, Formatter


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
        self.print_jobs()

    def add_guild_job(self, func: Callable, run_date: datetime, jobstore: str, **kwargs):
        self.add_job(func, 'date', run_date=run_date, jobstore=f"{self.info.get_id()}_{jobstore}", **kwargs)

    def init_save_player_data(self):
        today = datetime.datetime.today()
        if today.weekday() > self.save_day_num or \
                today.weekday() == self.save_day_num and today.time().hour >= self.save_time:
            self.info.save_players()

        self.add_job(self.info.save_players,
                     trigger=CronTrigger(day_of_week=self.save_day_num, hour=self.save_time),
                     jobstore=f"{self.info.get_id()}_maintenance")

    def init_auto_update(self, server_info):
        update_interval = self.config['update_interval']
        self.add_job(server_info.update, 'interval', minutes=update_interval, id="update_schedule",
                     jobstore=f"{self.info.get_id()}_maintenance")

    def _add_ping(self, date, channel, msg_start, time_offset, search_list, intervals=(0,)):
        item = search_list[time_offset]
        time = datetime.datetime.combine(date, datetime.time(16 + time_offset))
        for interval in intervals:
            run_time = time - datetime.timedelta(minutes=interval)
            message = f"{msg_start} {item} in {interval} minutes"
            day_name = Formatter.day_name(date.weekday())
            ping_id = f"{day_name} {time_offset} {interval}"
            self.add_guild_job(
                channel.send,
                run_time,
                "pings",
                name=item,
                args=[message],
                id=ping_id,
                replace_existing=True
            )

    # TODO: Add more methods for updating the ping jobstore instead of just wiping it every update
        # ^ maybe only do this if pinging for every activity becomes a thing again
    def init_schedule_pings(self, channel, info: BaseInfo):
        config = info.config
        role_mention = config['role_mention']
        remind_activities = [activity.lower() for activity in config['remind_activities']]
        remind_intervals = config['remind_intervals']

        today = datetime.date.today().weekday()
        days = info.week_schedule.days
        start_date = days[0].as_date()

        for day_index, day in enumerate(days[today::]):
            date = start_date + datetime.timedelta(days=day_index)

            first_activity = day.first_activity(remind_activities)
            if first_activity != -1:
                # post the schedule at 9 AM
                morning_runtime = datetime.datetime.combine(date, datetime.time(9))
                morning_ping_id = day.name + "_morning_ping"
                embed = get_formatter(info, 'PST').get_day_schedule(
                    info.players,
                    day_index
                )
                self.add_guild_job(
                    channel.send,
                    morning_runtime,
                    "pings",
                    kwargs={'embed': embed},
                    id=morning_ping_id,
                    replace_existing=True
                )

                # TODO: check for existing jobs and modify them on update instead of replacing them entirely maybe
                self._add_ping(date, channel, role_mention, first_activity, day.activities, intervals=remind_intervals)

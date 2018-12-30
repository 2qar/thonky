from apscheduler.schedulers.asyncio import AsyncIOScheduler
import datetime
import calendar
import json
from typing import Callable

from .server_info import ServerInfo
from .formatter import get_formatter, Formatter
from .dbhandler import DBHandler


# TODO: Eventually rewrite the whole jobstore thing
#       Instead of each ServerInfo having it's own maintenance and pings jobstore,
#       have one maintenance and pings jobstore on the scheduler and use functions to manage jobs from multiple servers
class PingScheduler(AsyncIOScheduler):
    def __init__(self):
        super().__init__()
        self.start()
        self.guild_id = 0

        with open('config.json') as file:
            self.config = json.load(file)
        self.save_day_num = list(calendar.day_name).index(self.config['save_day'].title())

    def has_guild(self, guild_id: int):
        try:
            return bool(self._lookup_jobstore(f"{guild_id}_pings"))
        except KeyError:
            return False

    def setup_guild(self, server_info: ServerInfo):
        for key, jobstore in server_info.jobstores.items():
            self.add_jobstore(jobstore, alias=f"{server_info.guild_id}_{key}")

        self.guild_id = server_info.guild_id
        self.init_save_player_data(server_info)
        self.init_auto_update(server_info)
        channel = server_info.get_ping_channel()
        if channel:
            self.init_schedule_pings(channel, server_info)
        self.print_jobs()

    def add_guild_job(self, func: Callable, run_date: datetime, jobstore: str, **kwargs):
        self.add_job(func, 'date', run_date=run_date, jobstore=f"{self.guild_id}_{jobstore}", **kwargs)

    def init_save_player_data(self, server_info, save_day=None):
        save_time = self.config['save_time']

        # gets save day first time this method is called or gets next save day from previous save day given
        if save_day is None:
            today = datetime.date.today()
            monday = today - datetime.timedelta(days=today.weekday())
            save_day = monday + datetime.timedelta(days=self.save_day_num)
        else:
            save_day += datetime.timedelta(days=self.save_day_num + 1)

        today = datetime.datetime.today()
        automated_save_missed = today.weekday() == self.save_day_num and today.hour >= save_time
        save_time_as_date = datetime.time(save_time)
        if automated_save_missed:
            server_info.save_players()
            next_save_day = today + datetime.timedelta(days=self.save_day_num)
            run_time = datetime.datetime.combine(next_save_day.date(), save_time_as_date)
        else:
            run_time = datetime.datetime.combine(save_day, save_time_as_date)

        self.add_guild_job(server_info.save_players, run_time, "maintenance")
        self.add_guild_job(self.init_save_player_data, run_time, "maintenance", args=[save_day])

    def init_auto_update(self, server_info):
        update_interval = self.config['update_interval']
        self.add_job(server_info.update, 'interval', minutes=update_interval, id="update_schedule")

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
                run_date=run_time,
                args=[message],
                id=ping_id,
                replace_existing=True
            )

    # TODO: Add more methods for updating the ping jobstore instead of just wiping it every update
        # ^ maybe only do this if pinging for every activity becomes a thing again
    def init_schedule_pings(self, channel, server_info: ServerInfo):
        with DBHandler() as handler:
            config = handler.get_server_config(server_info.guild_id)
            role_mention = config['role_mention']
            remind_activities = [activity.lower() for activity in config['remind_activities']]
            remind_intervals = config['remind_intervals']

        today = datetime.date.today().weekday()
        days = server_info.week_schedule.days
        start_date = days[0].as_date()

        for day_index, day in enumerate(days[today::]):
            date = start_date + datetime.timedelta(days=day_index)

            first_activity = day.first_activity(remind_activities)
            if first_activity != -1:
                # post the schedule at 9 AM
                morning_runtime = datetime.datetime.combine(date, datetime.time(9))
                morning_ping_id = day.name + "_morning_ping"
                embed = get_formatter('PST').get_day_schedule(
                    server_info.guild_id,
                    server_info.players,
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

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.memory import MemoryJobStore
import datetime
import calendar
import json

from .formatter import get_formatter
from .dbhandler import DBHandler


class PingScheduler(AsyncIOScheduler):
    def __init__(self, server_id, server_info):
        super().__init__()
        self.start()
        self.add_jobstore(MemoryJobStore(), alias='pings')
        self.add_jobstore(MemoryJobStore(), alias='vods')

        self.server_id = server_id
        with open('config.json') as file:
            self.config = json.load(file)
        self.server_info = server_info
        self.save_day_num = list(calendar.day_name).index(self.config['save_day'].title())

    def init_scheduler(self, server_info):
        #TODO: Load config once and pass it to the 3 methods below
        #with DBHandler() as handler:
            #self.server_info(

        self.init_save_player_data(server_info)
        self.init_auto_update(server_info)
        channel = server_info.get_ping_channel()
        if channel:
            self.init_schedule_pings(channel)
        self.print_jobs()

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

        self.add_job(server_info.save_players, 'date', run_date=run_time)
        self.add_job(self.init_save_player_data, 'date', run_date=run_time, args=[save_day])

    def init_auto_update(self, server_info):
        update_interval = self.config['update_interval']
        self.add_job(server_info.update, 'interval', minutes=update_interval, id="update_schedule")

    # TODO: Add more methods for updating the ping jobstore instead of just wiping it every update
    def init_schedule_pings(self, channel):
        with DBHandler() as handler:
            config = handler.get_server_config(self.server_id)
            role_mention = config['role_mention']
            remind_activities = [activity.lower() for activity in config['remind_activities']]
            remind_intervals = config['remind_intervals']

        today = datetime.date.today().weekday()
        days = self.server_info.week_schedule.days
        start_date = days[0].as_date()

        for day_index in range(today, len(days)):
            date = start_date + datetime.timedelta(days=day_index)
            day = days[day_index]

            # TODO: Unique job ID for VODs, better ID for days
            def add_reminders(msg_start, index, search_list, jobstore, id=None):
                item = search_list[index]
                time = datetime.datetime.combine(date, datetime.time(16 + index))
                for interval in remind_intervals:
                    run_time = time - datetime.timedelta(minutes=interval)
                    message = f"{msg_start} {item} in {interval} minutes"
                    ping_id = str(index) if not id else f"{id} {interval} min reminder"
                    self.add_job(
                        channel.send,
                        'date',
                        run_date=run_time,
                        args=[message],
                        id=ping_id,
                        replace_existing=True,
                        jobstore=jobstore
                    )

            # FIXME: no VODs being scheduled
            vods = day.get_vods()
            for vod in vods:
                add_reminders("Player VOD for", vod, day.notes, 'vods')
            for job in self.get_jobs(jobstore='vods'):
                if not int(job.id) in vods:
                    self.remove_job(job.id, jobstore='vods')

            first_activity = day.first_activity(remind_activities)
            if first_activity != -1:
                # post the schedule at 9 AM
                morning_runtime = datetime.datetime.combine(date, datetime.time(9))
                morning_ping_id = day.name + "_morning_ping"
                embed = get_formatter('PST').get_day_schedule(self.server_id, self.server_info.players, day_index)
                self.add_job(
                    channel.send,
                    'date',
                    run_date=morning_runtime,
                    kwargs={'embed': embed},
                    id=morning_ping_id,
                    replace_existing=True,
                    jobstore='pings'
                )

                add_reminders(role_mention, first_activity, day.activities, 'pings', id=day)

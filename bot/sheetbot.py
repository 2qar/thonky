from gspread import Client, Cell, Worksheet
from oauth2client.service_account import ServiceAccountCredentials
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from datetime import datetime, timedelta
from dateutil.parser import parse
from typing import List, Tuple, Dict

from .creds_helper import get_creds
from .players import Player
from .players import Players
from .schedules import DaySchedule
from .schedules import WeekSchedule


def strip_microseconds(dt: datetime) -> datetime:
    return dt - timedelta(microseconds=dt.microsecond)


def stripped_utcnow() -> datetime:
    return strip_microseconds(datetime.utcnow())


def check_creds(func):
    def wrapper(*args):
        self: SheetHandler = args[0]
        if stripped_utcnow() > self.expiry:
            self.auth.refresh(Request())
        return func(*args)
    return wrapper


class SheetHandler(Client):
    """ Used for snatching some useful information from a sheet using a given doc key """

    script_scope = ['https://www.googleapis.com/auth/script.projects', 'https://www.googleapis.com/auth/spreadsheets']
    script_id = '1LPgef8gEDpefvna6p9AZVKrqvpNqWVxRD6yOhYZgFSs3QawU1ktypVEm'

    @staticmethod
    def _get_expiry():
        return stripped_utcnow() + timedelta(seconds=ServiceAccountCredentials.MAX_TOKEN_LIFETIME_SECS)

    def __init__(self, doc_key):
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        self.auth = ServiceAccountCredentials.from_json_keyfile_name('creds/service_account.json', scope)
        super().__init__(self.auth)
        self.login()

        self.expiry = self._get_expiry()
        self.doc_key = doc_key
        self.last_modified = self._get_last_modified_time()

    @staticmethod
    def _get_service(service_type, version, scopes):
        return build(service_type, version, credentials=get_creds(service_type, scopes))

    def _get_sheet(self, sheet_name) -> Worksheet:
        return self.open_by_key(self.doc_key).worksheet(sheet_name)

    def _get_last_modified_time(self):
        service = self._get_service('drive', 'v3', ['https://www.googleapis.com/auth/drive'])
        response = service.files().get(fileId=self.doc_key, fields='modifiedTime').execute()

        modified_time = response['modifiedTime']
        modified_time = modified_time[:modified_time.rfind('.')]
        return parse(modified_time)

    def update_modified(self):
        """ Set last_modified to right now without the whole microsecond junk """
        self.last_modified = stripped_utcnow()

    @property
    def updated(self):
        modified_time = self._get_last_modified_time()

        if modified_time <= self.last_modified:
            return True

        return False

    @check_creds
    def get_players(self) -> Players:
        """ Get all of the players in a nice little bundle :) """

        availability = self._get_sheet("Team Availability")

        print("Getting player cells...")
        player_range_end = availability.find("Tanks Available:").row
        player_range = "C4:C" + str(player_range_end)
        player_cells = availability.range(player_range)

        role = ""
        players = []
        sorted_players = {}

        print("Creating player objects...")
        for cell in player_cells:
            if cell.value != '':
                cells = availability.range('A{0}:C{0}'.format(cell.row))
                vals = [val.value for val in cells]
                if vals[1] != '':
                    role = vals[1]
                    sorted_players[role] = []
                name = vals[2]

                player_doc = self._get_sheet(name)
                if player_doc:
                    available_times: List[Cell] = player_doc.range('C3:H9')
                    for i, response in enumerate(available_times):
                        if response == '':
                            available_times[i].value = 'Nothing'

                    players.append(Player(name, role, available_times))

        for player in players:
            sorted_players[player.role].append(player)

        player_obj = Players(sorted_players, players)

        print("Done! :)")
        return player_obj

    @check_creds
    def get_valid_activities(self) -> List[str]:
        """ Get a list of valid activities to write to the weekly schedule """

        service = SheetHandler._get_service('sheets', 'v4', [SheetHandler.script_scope[1]])
        response = service.spreadsheets().get(
            spreadsheetId=self.doc_key,
            fields='sheets(properties(title,sheetId),conditionalFormats)'
        ).execute()
        week_formats = response['sheets'][1]['conditionalFormats']

        def get_value(rule: Dict): return rule['booleanRule']['condition']['values'][0]['userEnteredValue']
        return [get_value(rule) for rule in week_formats]

    @check_creds
    def get_week_schedule(self) -> WeekSchedule:
        """ Returns a week schedule object for getting the activities for each day n stuff """

        # get all of the cell notes
        request = {'function': 'getCellNotes', 'parameters': [self.doc_key, 'C3:H9']}
        service = SheetHandler._get_service('script', 'v1', SheetHandler.script_scope)
        response = service.scripts().run(body=request, scriptId=SheetHandler.script_id).execute()
        try:
            notes = response['response']['result']
        except KeyError:
            print(f"ERROR grabbing notes on sheet with key [{self.doc_key}]."
                  f"\nDoes your Google account you authenticated this app with have read access on the spreadsheet?")
            notes = [''] * 6

        activity_sheet = self._get_sheet("Weekly Schedule")
        day_rows = activity_sheet.range("B3:B9")

        def get_day(row, given_notes):
            split = row.value.split()

            name = split[0]
            name = name[0:len(name)-1]

            date = split[1]

            row_range = "C{0}:H{0}".format(row.row)
            activity_cells = activity_sheet.range(row_range)

            return DaySchedule(name, date, activity_cells, given_notes)

        days = [get_day(row, note) for row, note in zip(day_rows, notes)]

        return WeekSchedule(days)

    @check_creds
    def update_cells(self, sheet_name: str, cells: List[Cell], values: List[str]) -> Tuple[List[str], List[str]]:
        """ Updates a range of cells and returns the values before and after. """

        sheet = self._get_sheet(sheet_name)

        if len(values) != len(cells) and len(values) != 1:
            raise IndexError("Length of values given doesn't match the amount of cells.")

        before = [cell.value for cell in cells]
        if len(values) > 1:
            for i, cell in enumerate(cells):
                cell.value = values[i]
        else:
            for cell in cells:
                cell.value = values[0]
        sheet.update_cells(cells)
        self.update_modified()

        return before, values

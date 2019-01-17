from gspread import Client, Cell, Worksheet, Spreadsheet
from oauth2client.service_account import ServiceAccountCredentials
from google.auth.transport.requests import Request
from datetime import datetime, timedelta
from dateutil.parser import parse
from typing import List, Tuple, Dict

from .creds_helper import get_service
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
        self: Sheet = args[0]
        if self._sheet_handler.expired:
            self._sheet_handler.auth.refresh(Request())
        return func(*args)
    return wrapper


class SheetHandler(Client):
    """ Used for snatching some useful information from a sheet using a given doc key """

    @staticmethod
    def _get_expiry():
        return stripped_utcnow() + timedelta(seconds=ServiceAccountCredentials.MAX_TOKEN_LIFETIME_SECS)

    def __init__(self):
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        self.auth = ServiceAccountCredentials.from_json_keyfile_name('creds/service_account.json', scope)
        super().__init__(self.auth)
        self.login()

        self.expiry = self._get_expiry()

    @property
    def expired(self):
        return stripped_utcnow() > self.expiry

    def get_sheet(self, doc_key: str):
        return Sheet(self, doc_key)


# TODO: Better logging
class Sheet(Spreadsheet):
    def __init__(self, sheet_handler: SheetHandler, doc_key):
        super().__init__(sheet_handler, {'id': doc_key})

        self._sheet_handler = sheet_handler
        self._last_modified = self._get_last_modified()

    @property
    def updated(self):
        return bool(self._get_last_modified() <= self._last_modified)

    def _get_last_modified(self):
        service = get_service('drive', 'v3')
        response = service.files().get(fileId=self.id, fields='modifiedTime').execute()

        modified_time = response['modifiedTime']
        modified_time = modified_time[:modified_time.rfind('.')]
        return parse(modified_time)

    def update_modified(self):
        """ Set last_modified to right now without the whole microsecond junk """
        self._last_modified = stripped_utcnow()

    @check_creds
    def get_players(self) -> Players:
        """ Get all of the players in a nice little bundle :) """

        availability = self.worksheet("Team Availability")

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

                player_doc = self.worksheet(name)
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

        service = get_service('sheets', 'v4')
        response = service.spreadsheets().get(
            spreadsheetId=self.id,
            fields='sheets(properties(title,sheetId),conditionalFormats)'
        ).execute()
        week_formats = response['sheets'][1]['conditionalFormats']

        def get_value(rule: Dict): return rule['booleanRule']['condition']['values'][0]['userEnteredValue']
        return [get_value(rule) for rule in week_formats]

    @check_creds
    def get_week_schedule(self) -> WeekSchedule:
        """ Returns a week schedule object for getting the activities for each day n stuff """

        # get all of the cell notes
        request = {'function': 'getCellNotes', 'parameters': [self.id, 'C3:H9']}
        service = get_service('script', 'v1')
        response = service.scripts().run(
            body=request,
            scriptId='1LPgef8gEDpefvna6p9AZVKrqvpNqWVxRD6yOhYZgFSs3QawU1ktypVEm').execute()
        try:
            notes = response['response']['result']
        except KeyError:
            print(f"ERROR grabbing notes on sheet with key [{self.id}]."
                  f"\nDoes your Google account you authenticated this app with have read access on the spreadsheet?")
            notes = [''] * 6

        activity_sheet = self.worksheet("Weekly Schedule")
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

        sheet = self.worksheet(sheet_name)

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

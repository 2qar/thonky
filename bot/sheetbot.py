from gspread_asyncio import AsyncioGspreadClientManager, AsyncioGspreadClient, Cell, AsyncioGspreadSpreadsheet
from oauth2client.service_account import ServiceAccountCredentials
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
    async def wrapper(*args):
        self: Sheet = args[0]
        await self._update_sheet_creds()
        return await func(*args)
    return wrapper


class SheetHandler(AsyncioGspreadClientManager):
    """ Used for snatching some useful information from a sheet using a given doc key """

    @staticmethod
    def _get_service_creds():
        return ServiceAccountCredentials.from_json_keyfile_name(
            'creds/service_account.json',
            ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        )

    def __init__(self):
        super().__init__(self._get_service_creds)

        self.gc: AsyncioGspreadClient = None

    @property
    def expired(self):
        return self.auth_time is None or self.auth_time + self.reauth_interval < self._loop.time()

    async def init(self):
        self.gc = await self.authorize()

    async def get_sheet(self, doc_key: str):
        await self.init()
        return Sheet(self, await self.gc.open_by_key(doc_key))


# TODO: Better logging
class Sheet:
    def __init__(self, handler: SheetHandler, sheet: AsyncioGspreadSpreadsheet):
        self._handler = handler
        self._sheet = sheet
        self._last_modified = self._get_last_modified()

    async def _update_sheet_creds(self):
        await self._handler.init()
        self._sheet = await self._handler.gc.open_by_key(self._sheet.id)

    @property
    def id(self):
        return self._sheet.id

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
    async def get_players(self) -> Players:
        """ Get all of the players in a nice little bundle :) """

        availability = await self._sheet.worksheet("Team Availability")

        print("Getting player cells...")
        player_range_end = await availability.find("Tanks Available:")
        player_range_end = player_range_end.row
        player_range = "C4:C" + str(player_range_end)
        player_cells = await availability.range(player_range)

        role = ""
        players = []
        sorted_players = {}

        print("Creating player objects...")
        for cell in player_cells:
            if cell.value != '':
                cells = await availability.range('A{0}:C{0}'.format(cell.row))
                vals = [val.value for val in cells]
                if vals[1] != '':
                    role = vals[1]
                    sorted_players[role] = []
                name = vals[2]

                player_doc = await self._sheet.worksheet(name)
                if player_doc:
                    available_times: List[Cell] = await player_doc.range('C3:H9')
                    for i, response in enumerate(available_times):
                        if response == '':
                            available_times[i].value = 'Nothing'

                    players.append(Player(name, role, available_times))

        for player in players:
            sorted_players[player.role].append(player)

        player_obj = Players(sorted_players, players)

        print("Done! :)")
        return player_obj

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
    async def get_week_schedule(self) -> WeekSchedule:
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

        activity_sheet = await self._sheet.worksheet("Weekly Schedule")
        day_rows = await activity_sheet.range("B3:B9")

        async def get_day(row, given_notes):
            split = row.value.split()

            name = split[0]
            name = name[0:len(name)-1]

            date = split[1]

            row_range = "C{0}:H{0}".format(row.row)
            activity_cells = await activity_sheet.range(row_range)

            return DaySchedule(name, date, activity_cells, given_notes)

        days = [await get_day(row, note) for row, note in zip(day_rows, notes)]

        return WeekSchedule(days)

    @check_creds
    async def update_cells(self, sheet_name: str, cells: List[Cell], values: List[str]) -> Tuple[List[str], List[str]]:
        """ Updates a range of cells and returns the values before and after. """

        sheet = await self._sheet.worksheet(sheet_name)

        if len(values) != len(cells) and len(values) != 1:
            raise IndexError("Length of values given doesn't match the amount of cells.")

        before = [cell.value for cell in cells]
        if len(values) > 1:
            for i, cell in enumerate(cells):
                cell.value = values[i]
        else:
            for cell in cells:
                cell.value = values[0]
        await sheet.update_cells(cells)
        self.update_modified()

        return before, values

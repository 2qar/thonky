import gspread
from gspread import Cell
from oauth2client.service_account import ServiceAccountCredentials
from googleapiclient.discovery import build
from httplib2 import Http
from oauth2client import file as oauth_file, client, tools
from typing import List, Tuple, Dict

from .players import Player
from .players import Players
from .schedules import DaySchedule
from .schedules import WeekSchedule


class SheetHandler:
    """ Used for snatching some useful information from a sheet using a given doc key """

    script_scope = ['https://www.googleapis.com/auth/script.projects', 'https://www.googleapis.com/auth/spreadsheets']
    script_id = '1LPgef8gEDpefvna6p9AZVKrqvpNqWVxRD6yOhYZgFSs3QawU1ktypVEm'

    def __init__(self, doc_key):
        self.doc_key = doc_key
        self.authenticate()

    def authenticate(self):
        """ Authenticates the bot for sheets access.
            Gotta call it before calling any of the other stuff. """

        print("Authenticating Google API...")
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        credentials = ServiceAccountCredentials.from_json_keyfile_name('creds/service_account.json', scope)
        self.gc = gspread.authorize(credentials)
        print("Authenticated.")

    @staticmethod
    def get_service(service_type, version, scope):
        store = oauth_file.Storage(f'creds/token.json')
        creds = store.get()
        if not creds or creds.invalid:
            flow = client.flow_from_clientsecrets('creds/client_secret.json', scope)
            creds = tools.run_flow(flow, store)
        return build(service_type, version, http=creds.authorize(Http()))

    def get_sheet(self, sheet_name):
        return self.gc.open_by_key(self.doc_key).worksheet(sheet_name)

    def get_players(self):
        """ Get all of the players in a nice little bundle :) """

        availability = self.get_sheet("Team Availability")

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
                cells = availability.range('A{0}:AS{0}'.format(cell.row))
                vals = [val.value for val in cells]
                if vals[1] != '':
                    role = vals[1]
                    sorted_players[role] = []
                name = vals[2]

                available_times = cells[3:]
                for time in range(0, len(available_times)):
                        if available_times[time].value == '':
                            available_times[time].value = 'Nothing'

                players.append(Player(name, role, available_times))

        for player in players:
            sorted_players[player.role].append(player)

        player_obj = Players(sorted_players, players)

        print("Done! :)")
        return player_obj

    def get_valid_activities(self) -> List[str]:
        """ Get a list of valid activities to write to the weekly schedule """

        service = SheetHandler.get_service('sheets', 'v4', SheetHandler.script_scope[1])
        response = service.spreadsheets().get(
            spreadsheetId=self.doc_key,
            fields='sheets(properties(title,sheetId),conditionalFormats)'
        ).execute()
        week_formats = response['sheets'][1]['conditionalFormats']

        def get_value(rule: Dict): return rule['booleanRule']['condition']['values'][0]['userEnteredValue']
        return [get_value(rule) for rule in week_formats]

    def get_week_schedule(self):
        """ Returns a week schedule object for getting the activities for each day n stuff """

        # get all of the cell notes
        request = {'function': 'getCellNotes', 'parameters': [self.doc_key, 'C3:H9']}
        service = SheetHandler.get_service('script', 'v1', SheetHandler.script_scope)
        response = service.scripts().run(body=request, scriptId=SheetHandler.script_id).execute()
        try:
            notes = response['response']['result']
        except KeyError:
            print(f"ERROR grabbing notes on sheet with key [{self.doc_key}]."
                  f"\nDoes your Google account you authenticated this app with have read access on the spreadsheet?")
            notes = [''] * 6

        activity_sheet = self.get_sheet("Weekly Schedule")
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

    def update_cells(self, sheet_name: str, cells: List[Cell], values: List[str]) -> Tuple[List[str], List[str]]:
        """ Updates a range of cells and returns the values before and after. """

        sheet = self.get_sheet(sheet_name)

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

        return before, values

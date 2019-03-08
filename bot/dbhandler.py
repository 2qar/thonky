from typing import Any, List
from gspread import Cell
import psycopg2
import json
from datetime import datetime

from .helpers import strip_microseconds
from .players import Player, Players
from .schedules import DaySchedule, WeekSchedule


def dictify(data, fields):
    """ Convert a tuple to a dict with the given keys """
    formatted_data = {}
    for i, key in enumerate(fields):
            formatted_data[key] = data[i]
    return formatted_data


def server_id_check(guild_id: int) -> str:
    return f"AND server_id = '{guild_id}'"


class DBHandler:
    def __init__(self):
        with open('config.json') as config_file:
            cfg = json.load(config_file)
        self.conn = psycopg2.connect(dbname='thonkydb', user=cfg['db_user'], password=cfg['db_pw'], host=cfg['db_host'])
        self.cursor = self.conn.cursor()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def _get_template_config(self) -> dict:
        """ Template config for a guild or team """
        template_config = self.get_server_config(0)
        empty_keys = [key for key in template_config if not template_config[key]]
        for key in empty_keys:
            del(template_config[key])
        return template_config

    def _str_mogrify(self, query, values):
        return self.cursor.mogrify(query, values).decode("utf-8")

    def _get_check(self, field_name: str, value: Any, case_sensitive):
        """ Wrap the check in LOWER() if case_sensitive """

        if not value:
            return f"WHERE {field_name} IS NULL"
        elif not case_sensitive:
            return self._str_mogrify(f"WHERE LOWER({field_name}) = LOWER(%s)", (value,))
        else:
            return self._str_mogrify(f"WHERE {field_name} = %s", (value,))

    def _search(self, table_name: str, field_name: str, value: Any, case_sensitive=True, extra_query='',
                all_results=False) -> dict or None:
        """ Get row(s) from a table where a given field matches a given value.

            :param str extra_query: extra checks for searching
        """

        check = self._get_check(field_name, value, case_sensitive)
        self.cursor.execute(f"""
                SELECT * FROM {table_name}
                {check} {extra_query}
                """)
        results = self._format_sql_data(table_name)
        if results:
            if all_results:
                return results
            else:
                return results[0]
        return results

    def _update_many(self, table_name: str, check_field: str, check_value: Any, updates: dict, case_sensitive=True,
                     extra_query=''):
        """ Update row(s) from a table where a given field matches a given value. """

        check = self._get_check(check_field, check_value, case_sensitive)

        update_queries = []
        for key in updates:
            value = updates[key]
            if isinstance(value, dict):
               value = str(value).replace("'", '"')
            update_queries.append(self._str_mogrify(key, (value,)))

        # FIXME: update_string is just field names joined by AND instead of queries
        update_string = ' AND '.join(update_queries)
        self.cursor.execute(f"""
                UPDATE {table_name}
                SET {update_string}
                {check} {extra_query}
                """)
        self.conn.commit()

    def _update(self, table_name: str, check_field: str, check_value: Any, update_field: str, update_value: Any,
                case_sensitive=True, extra_query=''):
        self._update_many(table_name, check_field, check_value, {update_field: update_value},
                          case_sensitive=case_sensitive, extra_query=extra_query)

    def _add(self, table_name: str, guild_id: int, given_values: dict):
        """ Insert a new row with the given values. """

        given_values['server_id'] = guild_id

        def parenthesise(items: List[str]): return f"({', '.join(items)})"
        fields = []
        values = []
        for key in given_values:
            fields.append(key)
            value = given_values[key]
            if isinstance(value, dict):
                values.append(str(value).replace("'", '"'))
            else:
                values.append(value)

        formatted_fields = parenthesise([field for field in given_values])
        tuple_values = tuple(value for value in values)

        value_blanks = parenthesise(['%s' for key in values])

        self.cursor.execute(f"INSERT INTO {table_name} {formatted_fields} VALUES {value_blanks}", tuple_values)
        self.conn.commit()

    def get_server_config(self, server_id: int):
        return self._search('server_config', 'server_id', server_id)

    def update_server_config(self, server_id: int, key: str, value: Any):
        self._update('server_config', 'server_id', server_id, key, value)

    def add_server_config(self, server_id: int):
        self._add('server_config', server_id, self._get_template_config())

    def get_team_config(self, guild_id: int, team_name: str):
        return self._search('teams', 'team_name', team_name, case_sensitive=False,
                            extra_query=server_id_check(guild_id))

    def get_teams(self, guild_id: int):
        return self._search('teams', 'server_id', guild_id, all_results=True)

    def update_team_config(self, guild_id: int, team_name: str, key: str, value: Any):
        return self._update('teams', 'team_name', team_name, key, value, case_sensitive=True,
                            extra_query=server_id_check(guild_id))

    def add_team_config(self, guild_id: int, team_name: str, channel: int):
        template_config = self._get_template_config()
        template_config['team_name'] = team_name
        template_config['channels'] = [channel]
        self._add('teams', guild_id, template_config)

    def get_player_data(self, server_id: int, name: str, date=''):
        date_check = f"AND date = '{date}'" if date else ''
        extra_query = f"{server_id_check(server_id)} {date_check}"
        return self._search('player_data', 'name', name, case_sensitive=False, extra_query=extra_query)

    def add_player_data(self, server_id: int, name: str, date: str, availability: dict):
        self._add('player_data', server_id, {'name': name, 'date': date, 'availability': availability})

    def get_sheet_cache(self, server_id: int, team_name: str):
        return self._search('cache', 'team_name', team_name, extra_query=server_id_check(server_id))

    def update_sheet_cache(self, server_id: int, team_name: str, key: str, value: dict):
        last_saved = strip_microseconds(datetime.now()).isoformat()
        id_check = server_id_check(server_id)
        if not self._search('cache', 'team_name', team_name, extra_query=id_check):
            self._add('cache', server_id, {key: value, 'last_saved': last_saved})
        else:
            self._update_many('cache', 'team_name', team_name, {key: value, 'last_saved': last_saved},
                              extra_query=id_check)

    def _get_table_fields(self, table_name: str):
        self.cursor.execute(f"""
                SELECT column_name FROM information_schema.columns
                WHERE table_name='{table_name}'""")
        fields = [field[0] for field in self.cursor.fetchall()]

        if 'server_id' in fields:
            fields = fields[1:]

        return fields

    def _format_sql_data(self, table_name: str) -> List[dict] or List:
        data = self.cursor.fetchall()
        fields = self._get_table_fields(table_name)

        if not data:
            return []

        if len(data) > 1:
            return [dictify(entry[1:], fields) for entry in data]
        else:
            return [dictify(data[0][1:], fields)]

    def close(self):
        self.cursor.close()
        self.conn.close()

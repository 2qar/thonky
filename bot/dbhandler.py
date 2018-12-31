from typing import Dict, Any, List
import psycopg2
import json


def format_arrays(string):
    """ Format arrays to be SQL friendly :) """
    return string.replace('[', '{').replace(']', '}')


def dictify(data, fields):
    """ Convert a tuple to a dict with the given keys """
    formatted_data = {}
    for i, key in enumerate(fields):
            formatted_data[key] = data[i]
    return formatted_data


def get_check(field_name: str, case_sensitive):
    """ Wrap the check in LOWER() if case_sensitive """
    return f"WHERE {field_name} = %s" if case_sensitive else "WHERE LOWER({field_name}) = LOWER(%s)"


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

    def _search(self, table_name: str, field_name: str, value: Any, case_sensitive=True, extra_query='',
                all_results=False):
        """ Get row(s) from a table where a given field matches a given value.

            :param str extra_query: extra checks for searching
        """

        check = get_check(field_name, case_sensitive)
        self.cursor.execute(f"""
                SELECT * FROM {table_name}
                {check} {extra_query}
                """, (value,))
        results = self._format_sql_data(table_name)
        if all_results:
            return results
        else:
            return results[0]

    def _update(self, table_name: str, check_field: str, check_value: Any, update_field: str, update_value: Any,
                case_sensitive=True, extra_query=''):
        """ Update row(s) from a table where a given field matches a given value. """

        check = get_check(check_field, case_sensitive)
        self.cursor.execute(f"""
                UPDATE {table_name}
                SET {update_field} = %s
                {check} {extra_query}
                """, (update_value, check_value))
        self.conn.commit()

    def get_server_config(self, server_id: int):
        return self._search('server_config', 'server_id', server_id)

    def update_server_config(self, server_id: int, key: str, value: Any):
        self._update('server_config', 'server_id', server_id, key, value)

    def get_team_config(self, team_name: str):
        return self._search('teams', 'team_name', team_name, case_sensitive=False)

    def update_team_config(self, guild_id: int, team_name: str, key: str, value: Any):
        extra_query = f"AND server_id = '{guild_id}'"
        return self._update('teams', 'name', team_name, key, value, case_sensitive=True, extra_query=extra_query)

    def get_teams(self, guild_id: int):
        return self._search('teams', 'server_id', guild_id, all_results=True)

    def get_player_data(self, server_id: int, name: str, date=''):
        date_check = f"AND date = '{date}'" if date else ''
        extra_query = f"AND server_id = {server_id} {date_check}"
        return self._search('player_data', 'name', name, case_sensitive=False, extra_query=extra_query)

    def add_server_config(self, server_id: int):
        with open('config_base.json') as base:
            config_base = json.load(base)

        formatted_config_base = f"'{server_id}', "

        def format_item(key):
            value = str(config_base[key[0]])
            value = value.replace("'", '"')
            value = f"'{value}'"
            if value != "''":
                return value
            else:
                return 'NULL'

        formatted_config_base += ', '.join([format_item(key) for key in sorted(config_base.items())])
        formatted_config_base = format_arrays(formatted_config_base)

        query = f"""
                INSERT INTO server_config
                VALUES ({formatted_config_base})
                """
        self.cursor.execute(query)
        self.conn.commit()

    def add_player_data(self, server_id: int, name: str, date: str, availability: Dict):
        friendly_availability = str(availability).replace("'", '"')
        query = f"""
                INSERT INTO player_data (server_id, name, date, availability)
                VALUES ('{server_id}', '{name}', '{date}', '{friendly_availability}')
                """

        self.cursor.execute(query)
        self.conn.commit()

    def _get_table_fields(self, table_name: str):
        self.cursor.execute(f"""
                SELECT column_name FROM information_schema.columns
                WHERE table_name='{table_name}'""")
        fields = [field[0] for field in self.cursor.fetchall()]

        if 'server_id' in fields:
            fields = fields[1:]

        return fields

    def _format_sql_data(self, table_name: str) -> List[Dict] or List:
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

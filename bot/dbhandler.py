from typing import Any, List
import psycopg2
import json


def dictify(data, fields):
    """ Convert a tuple to a dict with the given keys """
    formatted_data = {}
    for i, key in enumerate(fields):
            formatted_data[key] = data[i]
    return formatted_data


def get_check(field_name: str, case_sensitive):
    """ Wrap the check in LOWER() if case_sensitive """
    return f"WHERE {field_name} = %s" if case_sensitive else f"WHERE LOWER({field_name}) = LOWER(%s)"


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

    def _search(self, table_name: str, field_name: str, value: Any, case_sensitive=True, extra_query='',
                all_results=False) -> dict or None:
        """ Get row(s) from a table where a given field matches a given value.

            :param str extra_query: extra checks for searching
        """

        check = get_check(field_name, case_sensitive)
        self.cursor.execute(f"""
                SELECT * FROM {table_name}
                {check} {extra_query}
                """, (value,))
        results = self._format_sql_data(table_name)
        if results:
            if all_results:
                return results
            else:
                return results[0]
        return results

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

    def _add(self, table_name: str, guild_id: int, given_values: dict):
        """ Insert a new row with the given values. """

        given_values['server_id'] = guild_id

        def parenthesise(items: List[str]): return f"({', '.join(items)})"
        fields = []
        values = []
        for key in given_values:
            fields.append(key)
            values.append(given_values[key])

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

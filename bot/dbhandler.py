import typing
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

    def get_table_fields(self, table_name: str):
        self.cursor.execute(f"""
                SELECT column_name FROM information_schema.columns
                WHERE table_name='{table_name}'""")
        fields = [field[0] for field in self.cursor.fetchall()]

        if 'server_id' in fields:
            fields = fields[1:]

        return fields

    def get_server_config(self, server_id: int):
        self.cursor.execute("""
                SELECT * FROM server_config 
                WHERE server_id = %s
                """,
                (server_id,))

        return self.format_sql_data('server_config')

    def add_server_config(self, server_id: int):
        with open('config_base.json') as base:
            config_base = json.load(base)

        formatted_config_base = f"'{server_id}', "

        def format_item(key):
            value = str(config_base[key[0]])
            value = value.replace("'", '"')
            return f"'{value}'"

        formatted_config_base += ', '.join([format_item(key) for key in sorted(config_base.items())])
        formatted_config_base = format_arrays(formatted_config_base)

        query = f"""
                INSERT INTO server_config
                VALUES ({formatted_config_base})
                """
        self.cursor.execute(query)
        self.conn.commit()

    def update_server_config(self, server_id: int, key: str, value):
        query = f"""
                UPDATE server_config
                SET {key} = '{value}'
                WHERE server_id = '{server_id}'
                """
        query = format_arrays(query)
        self.cursor.execute(query)
        self.conn.commit()

    def get_player_data(self, server_id: int, name: str, date: typing.Optional[str]=None):
        date_str = f"AND date = '{date}'" if date else ''
        self.cursor.execute(f"""
                SELECT * FROM player_data
                WHERE server_id = %s AND
                LOWER(name) = LOWER(%s) {date_str}
                """,
                (server_id, name))

        return self.format_sql_data('player_data')

    def add_player_data(self, server_id: int, name: str, date: str, availability: typing.Dict):
        friendly_availability = str(availability).replace("'", '"')
        query = f"""
                INSERT INTO player_data (server_id, name, date, availability)
                VALUES ('{server_id}', '{name}', '{date}', '{friendly_availability}')
                """

        self.cursor.execute(query)
        self.conn.commit()

    def format_sql_data(self, table_name: str):
        data = self.cursor.fetchall()
        fields = self.get_table_fields(table_name)

        if not data:
            return

        if len(data) > 1:
            return [dictify(entry[1:], fields) for entry in data]
        else:
            return dictify(data[0][1:], fields)

    def close(self):
        self.cursor.close()
        self.conn.close()

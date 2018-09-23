import psycopg2
import yaml
import json
import os

def format_arrays(string):
	""" Format arrays to be SQL friendly :) """
	return string.replace('[', '{').replace(']', '}')

def dictify(data, fields):
	""" Convert a tuple to a dict with the given keys """
	formatted_data = {}
	for i, key in enumerate(fields):
		formatted_data[key] = data[i]
	return formatted_data


class DBHandler():
	server_config_fields = ['announce_channel', 'doc_key', 'non_reminder_activities', 'remind_intervals', 'role_mention', 'team_id', 'update_interval']
	player_data_fields = ['name', 'date', 'availability']

	def __init__(self):
		with open('config.yaml') as config_file:
			cfg = [doc for doc in yaml.safe_load_all(config_file)][-1]
		self.conn = psycopg2.connect(dbname=cfg['db_name'], user=cfg['db_user'], password=cfg['db_pass'], host=cfg['db_ip'])
		self.cursor = self.conn.cursor()

	def __enter__(self):
		return self

	def __exit__(self, exc_type, exc_val, exc_tb):
		self.close()

	def get_server_config(self, server_id):
		self.cursor.execute("""
			SELECT * FROM server_config 
			WHERE server_id = %s
			""", 
			(server_id,))

		return self.format_sql_data(DBHandler.server_config_fields)

	def add_server_config(self, server_id):
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
			INSERT INTO server_config (server_id, announce_channel, doc_key, non_reminder_activities, remind_intervals, role_mention, team_id, update_interval)
			VALUES ({formatted_config_base})
			"""
		self.cursor.execute(query)
		self.conn.commit()

	def update_server_config(self, server_id, key, value):
		query = f"""
			UPDATE server_config
			SET {key} = '{value}'
			WHERE server_id = '{server_id}'
			"""
		query = format_arrays(query)
		self.cursor.execute(query)
		self.conn.commit()

	def get_player_data(self, server_id, name, date=None):
		date_str = f"AND date = '{date}'" if date else ''
		self.cursor.execute(f"""
			SELECT * FROM player_data
			WHERE server_id = %s AND name = %s {date_str}
			""",
			(server_id, name))

		return self.format_sql_data(DBHandler.player_data_fields)

	def add_player_data(self, server_id, name, date, availability):
		friendly_availability = str(availability).replace("'", '"')
		query = f"""
			INSERT INTO player_data (server_id, name, date, availability)
			VALUES ('{server_id}', '{name}', '{date}', '{friendly_availability}')
			"""

		self.cursor.execute(query)
		self.conn.commit()

	def format_sql_data(self, fields):
		data = self.cursor.fetchall()

		if not data: return

		if len(data) > 1:
			return [dictify(entry[1:], fields) for entry in data]
		else:
			return dictify(data[0][1:], fields)
		
	def close(self):
		self.cursor.close()
		self.conn.close()
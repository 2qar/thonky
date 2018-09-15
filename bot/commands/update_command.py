import asyncio
import json
import os

from ..server_info import ServerInfo

#TODO: Make help method
#TODO: Make this work with server info
class UpdateCommand():
	async def invoke(bot, server_id, channel=None):
		should_send_messages = channel != None

		if server_id in bot.server_info:
			server_info = bot.server_info[server_id]
		else:
			try:
				with open(f"servers/{server_id}/config.json") as file:
					doc_key = json.load(file)['doc_key']
			except:
				error_msg = "ERROR: No doc key given for server, unable to update "
				if should_send_messages:
					await bot.send_message(channel, error_msg)
				print(error_msg + server_id)
				return

			info = ServerInfo(doc_key, server_id, bot, UpdateCommand.invoke)
			bot.server_info[server_id] = info
			print(f"Constructed ServerInfo for server with ID [{server_id}]")
			return

		if server_info.scanning: return

		server_info.scanning = True
		if should_send_messages: 
			await bot.send_message(channel, "Scanning sheet...")

		with open(f"servers/{server_id}/config.json") as config_file:
			config = json.load(config_file)
			config_doc_key = config['doc_key']
			if server_info.scraper.doc_key != config_doc_key:
				server_info.scraper.doc_key = config_doc_key

		server_info.update(bot)

		if should_send_messages: 
			await bot.send_message(channel, "Rescanned sheet.")
		server_info.scanning = False

	async def bulk_update(bot):
		for server_id in os.listdir('servers'):
			print(f"Updating server with ID [{server_id}]")
			await UpdateCommand.invoke(bot, server_id)

	async def help(bot, channel):
		pass

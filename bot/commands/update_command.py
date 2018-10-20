import asyncio
import json

from ..server_info import ServerInfo
from ..dbhandler import DBHandler

#TODO: Make help method
class UpdateCommand():
	async def invoke(bot, server_id, channel=None):
		should_send_messages = channel != None

		if server_id in bot.server_info:
			server_info = bot.server_info[server_id]
		else:
			with DBHandler() as handler:
				doc_key = handler.get_server_config(server_id)['doc_key']
				if not doc_key:
					error_msg = "ERROR: No doc key given for server, unable to update "
					if should_send_messages:
						await bot.send_message(channel, error_msg)
					print(error_msg + server_id)
					return
				else:
					info = ServerInfo(doc_key, server_id, bot, UpdateCommand.invoke)
					bot.server_info[server_id] = info
					print(f"Constructed ServerInfo for server with ID [{server_id}]")
					return
			
		if server_info.scanning: return

		server_info.scanning = True
		if should_send_messages: 
			await bot.send_message(channel, "Scanning sheet...")

		with DBHandler() as handler:
			config = handler.get_server_config(server_id)
			config_doc_key = config['doc_key']
			if server_info.scraper.doc_key != config_doc_key:
				server_info.scraper.doc_key = config_doc_key

		server_info.update(bot)

		if should_send_messages: 
			await bot.send_message(channel, "Rescanned sheet.")
		server_info.scanning = False

	async def help(bot, channel):
		pass

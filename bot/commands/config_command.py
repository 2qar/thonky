import asyncio
import json

from .update_command import UpdateCommand

#TODO: help command that prints out all of the available stuff to configure and their required arguments 
#TODO: !add <spreadsheet link> to get doc key
	#maybe !set_sheet or something
	#also do this for team_id and such

base_sheet_url = 'https://docs.google.com/spreadsheets/d/'
base_team_url = 'https://battlefy.com/teams/'

#TODO: Make this work (TypeError: coroutine not callable)
'''
async def start_check(arg_check, arg_fail):
	async def start_check_decorator(func, arg_check, arg_fail):
		async def func_wrapper(self, arg):
			if arg.startswith(arg_check):
				await bot.send_message(self.channel, arg_fail)
			else:
				return await func()
		return await func_wrapper()
	return start_check_decorator


class ConfigEditor:
	def __init__(self, bot, message):
		self.bot = bot
		self.message = message
		self.channel = message.channel
		self.server_id = message.server.id
	
	@start_check(base_sheet_url, "ERROR: Invalid spreadsheet link.")
	async def set_sheet(self, url):
		# cut the stuff surrounding the key
		doc_key = url[len(base_sheet_url):]
		doc_key = doc_key[:doc_key.find('/')]

		self.write_property('doc_key', doc_key)
	
		await UpdateCommand.invoke(self.bot, self.server_id, self.channel)
	
	@start_check(base_team_url, "ERROR: Invalid team link.")
	async def set_team(self, url):
		team_id = url[len(base_team_url):]
		self.write_property('team_id', team_id)
		return "Team link grabbed. Use `!get od <round number>` to get info on your match in that round."
	
	@start_check('<#', "ERROR: Invalid channel.")
	async def set_channel(self, announce_channel):
		# check for permission to send messages
		if not self.channel.permissions_for(self.message.server.me).send_messages:
			return "ERROR: I can't send messages in that channel. :("
		else:
			self.write_property('announce_channel', announce_channel)
			return "Successfully set reminder channel. Run `!update` to update the reminder list. :)"
	
	@start_check('<@&', "ERROR: Invalid role mention.")
	async def set_role(self, role_mention):
		self.write_property('role_mention', role_mention)
		return "Successfully set role mention. Run `!update` to update the reminder list. :)"

	def write_property(self, key, value):
		file_path = f"servers/{self.server_id}/config.json"
		with open(file_path) as config_file:
			config = json.load(config_file)
		with open(file_path, 'w') as config_file:
			config[key] = value
			config_file.write(json.dumps(config, indent=4, sort_keys=True))
'''

async def config(bot, message):
	server_id = message.server.id
	content = message.content
	channel = message.channel

	split = content.split()
	cmd = split[0].lower()

	if len(split) != 2:
		await bot.send_message(channel, "ERROR: Invalid number of arguments; one required.")
		return
	elif not channel.permissions_for(message.author).administrator:
		await bot.send_message(channel, "ERROR: You do not have permission to use this command.")
		return

	'''
	try:
		editor = ConfigEditor(bot, message)
		await get_attr(editor, cmd)(split[1])
	except Exception as e:
		await bot.send_message(channel, f"ERROR: Invalid config command. {e}")
	'''
	
	if cmd == '!set_sheet':
		url = split[1]
		if not url.startswith(base_sheet_url):
			await bot.send_message(channel, "ERROR: Invalid spreadsheet link.")
		else:
			doc_key = url[len(base_sheet_url):]
			key_end = doc_key.find('/')
			doc_key = doc_key[:key_end]

			# save the doc_key to the config
			write_property(server_id, 'doc_key', doc_key)

			await UpdateCommand.invoke(bot, server_id, channel)
	elif cmd == "!set_team":
		url = split[1]
		if not url.startswith(base_team_url):
			await bot.send_message(channel, "ERROR: Invalid team link.")
		else:
			team_id = url[len(base_team_url):]

			write_property(server_id, 'team_id', team_id)

			await bot.send_message(channel, "Team link grabbed. Use `!get od <round number>` to get info on your match in that round.")
	elif cmd == "!set_channel":
		channel = split[1]
		if not channel.startswith("<#"):
			await bot.send_messaeg(channel, "ERROR: Invalid channel.")
		else:
			# check for send permission
			if not channel.permissions_for(message.server.me).send_messages:
				await bot.send_message(channel, "ERROR: I can't send messages in that channel. :(")
			else:
				write_property(server_id, 'announce_channel', channel)
				await bot.send_message(channel, "Successfully set reminder channel. Run `!update` to update the reminder list. :)")
	elif cmd == "!set_role":
		role_mention = split[1]
		if not role_mention.startswith("<@&"):
			await bot.send_message(channel, "ERROR: Invalid role mention.")
		else:
			write_property(server_id, 'role_mention', role_mention)
			await bot.send_message(channel, "Successfully set role mention. Run `!update` to update the reminder list. :)")
			
def write_property(server_id, key, value):
	file_path = f"servers/{server_id}/config.json"
	with open(file_path) as config_file:
		config = json.load(config_file)
	with open(file_path, 'w') as config_file:
		config[key] = value
		config_file.write(json.dumps(config, indent=4, sort_keys=True))

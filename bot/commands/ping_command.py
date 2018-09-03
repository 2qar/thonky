import asyncio

ping_list = []

async def ping(bot, message):
	""" Try to create a ping from a given username """

	content = message.content.split()
	channel = message.channel

	if len(content) != 2:
		await bot.send_message(channel, "Invalid command: Weird message length")
		return

	search_user = content[1]
	ping_user = None
	for user in message.server.members:
		if user.name.lower() == search_user:
			ping_user = user.mention

	if ping_user:
		ping = Ping(channel, ping_user, message.author.mention)
		ping_list.append(ping)
		await ping.start(bot)
	else:
		await bot.send_message(channel, f"Unable to find user with name \"{search_user}\"")

def check_to_stop(message):
	""" Stops a ping in the list if the author sends "stop" or if the victim sends a message.
		Call in the bot's on_message function """

	content = message.content.lower()
	channel = message.channel
	author_mention = message.author.mention

	for ping in ping_list:
		if ping.channel == channel:
			if ping.user_mention == author_mention:
				ping.stop()
			elif ping.author_mention == author_mention and message.content == 'stop':
				ping.stop()

class Ping:
	def __init__(self, channel, user_mention, author_mention):
		self.channel = channel
		self.user_mention = user_mention
		self.author_mention = author_mention
		self.pinging = False

	async def start(self, bot):
		self.pinging = True
		while self.pinging:
			await bot.send_message(self.channel, self.user_mention)
			await asyncio.sleep(5)

	def stop(self):
		self.pinging = False
		del(self)

import asyncio

#TODO: Make help method
class UpdateCommand():
	async def invoke(bot, channel=None):
		should_send_messages = channel != None

		if bot.scanning: return

		bot.scanning = True
		if should_send_messages: 
			await bot.send_message(channel, "Scanning sheet...")

		bot.scraper.authenticate()
		bot.players = bot.scraper.get_players()
		bot.week_schedule = bot.scraper.get_week_schedule()
		bot.scheduler.init_schedule_pings(bot)

		if should_send_messages: 
			await bot.send_message(channel, "Rescanned sheet.")
		bot.scanning = False

	async def help(bot, channel):
		pass

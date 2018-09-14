import asyncio
import yaml

#TODO: help command that prints out all of the available stuff to configure and their required arguments 
async def config(bot, message):
	print("running config command")
	if message.content.lower() == "!config --help":
		# run the help command for this
		pass

	content = message.content
	channel = message.channel

	args = content.split()
	print(args)
	if len(args) == 2:
		await bot.send_message(channel, "ERROR: No args given.")
		return

	args = args[1:]
	config = [doc for doc in yaml.safe_load_all(open('config.yaml'))][1]
	print(config)

	setting = args[0].lower()
	args = args[1:]
	print(setting)
	print(args)
	if setting == "reminders":
		try:
			times = [int(time) for time in args]
			time_str = "times" if len(times) > 1 else "time"
			await bot.send_message(channel, f"Changing reminder {time_str} to {', '.join(times)} minutes before first activity.")
			stream = file('config.yaml', 'w')
		except Exception as e:
			await bot.send_message(channel, f"ERROR: Given times aren't integers, or maybe something else: {e}")
	else:
		await bot.send_message(channel, "ERROR: Given setting to change isn't actually a setting that can be changed. :)")

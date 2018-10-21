import sys
import json

from bot.bot import Bot

with open('config.json') as file:
	config = json.load(file)
	
if len(sys.argv) == 1:
	print("Starting bot with main token.")
	token = config['main_token']
elif sys.argv[1] == 'test':
	print("Starting bot with test token.")
	token = config['test_token']

bot = Bot(token)

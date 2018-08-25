import sys
import yaml

from bot.bot import Bot

config_docs = [doc for doc in yaml.safe_load_all(open('config.yaml'))]
config = config_docs[0]

token = None
if len(sys.argv) == 1:
	print("Starting bot with main token.")
	token = config['tokens']['main_token']
elif sys.argv[1] == 'test':
	print("Starting bot with test token.")
	token = config['tokens']['test_token']

bot = Bot(token, config_docs[1])

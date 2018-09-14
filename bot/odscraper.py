import aiohttp
import asyncio
from bs4 import BeautifulSoup

import random

fwb_id = '5b0853b7cececb03a3fbd8e2'
#fwb_id = '5b71ecf6bb5b5103e196301f'
team_link = 'https://dtmwra1jsgyb0.cloudfront.net/persistent-teams/'
fwb_link = team_link + fwb_id

match_link_base = 'https://battlefy.com/overwatch-open-division-north-america/2018-overwatch-open-division-season-3-north-america/5b5e98399a8f8503cd0a07fd/stage/{}/match/{}'

# raw player list: https://dtmwra1jsgyb0.cloudfront.net/tournaments/5b5e98399a8f8503cd0a07fd/participants
#players = aiohttp.get('https://dtmwra1jsgyb0.cloudfront.net/tournaments/5b5e98399a8f8503cd0a07fd/participants').json()

class LinkNotFound(Exception):
	"""Raised when an important link gives a status code other than 200"""

async def get_ow_player_info(name):
	name = name.replace('#', '-')
	user_agent = {'User-Agent': 'OpenDivisionBot'}
	link = 'https://www.overbuff.com/players/pc/{}'.format(name)
	async with aiohttp.request('GET', link, headers=user_agent) as info:
		if info.status != 200: return str(info.status)

		soup = BeautifulSoup(await info.text(), 'html.parser')

		def get_sr():
			skill_rating = soup.find(class_="player-skill-rating")
			if skill_rating == None: return 0
			return int(skill_rating.contents[0])

		def get_role():
			roles_container = soup.find(class_="table-data")
			if roles_container == None: return '???'

			roles = roles_container.contents[1]

			highest_wins = 0
			best_role = None
			for role in roles.contents:
				wins = int(role.contents[2].attrs['data-value'])

				role_name_container = role.contents[1]
				role_name = role_name_container.contents[0].string

				if wins > highest_wins:
					highest_wins = wins
					best_role = role_name

			return best_role
						
		sr = get_sr()
		role = get_role()

		if sr == 0 and role == '???': return "404"

		return {'sr': sr, 'role': role}


async def get_player_info(player_json, owner=False):
	user = None
	user = player_json['user'] if not owner else player_json

	player_info = {}
	player_info['name'] = user['username']

	battletag = ''
	try:
		battletag = user['inGameName']
	except:
		try:
			battletag = user['accounts']['battlenet']['battletag']
		except:
			pass
		
	player_info['info'] = await get_ow_player_info(battletag)

	return player_info


async def get_team_info(persistent_team_id):
	curr_link = team_link + persistent_team_id
	team_info = None
	async with aiohttp.request('GET', curr_link) as request:
		if request.status == 200:
			data = await request.json()
			data = data[0]

			team_info = {}
			team_info['name'] = data['name']
			#team_info['link'] = 'https://battlefy.com/teams/' + persistent_team_id
			team_info['logo'] = data['logoUrl']

			players = [await get_player_info(player) for player in data['persistentPlayers']]
			players.insert(0, await get_player_info(data['owner'], owner=True))
			team_info['players'] = players
			
			average_sr = 0
			player_total = 0
			for player in players:
				if not isinstance(player['info'], str):
					if player['info']['sr'] > 0:
						average_sr += player['info']['sr']
						player_total += 1
			average_sr /= player_total
			team_info['sr_avg'] = int(average_sr)
		elif request.status == 404:
			raise LinkNotFound("Team not found on Battlefy.")
		else:
			return str(request.status)

	return team_info

def get_team_id(team):
	# try here because apparently there can be matches where one of the teams just doesnt exist
	try:
		return team['team']['persistentTeamID']
	except:
		return None

async def get_match(od_round, team_id):
	'''
	Looks through all of the matches in od_round and returns the one with the given persistentTeamID
	:param str od_round: The round to get the match from, can be a num 1-10
	:param str team_id: The ID of the team on battlefy that we're grabbing a match for
	:return: A match dict or None if the match couldn't be found
	'''

	matches = 'https://dtmwra1jsgyb0.cloudfront.net/stages/5b74a1b106dda6039a96e712/rounds/{}/matches'.format(od_round)

	async with aiohttp.request('GET', matches) as request:
		if request.status == 404: raise LinkNotFound(f"Unable to get match in round {od_round}.")

		matches_json = await request.json()

		for match in matches_json:
			for key in ['top', 'bottom']:
				if get_team_id(match[key]) == team_id:
					return match

# import this method into formatter
async def get_other_team_info(od_round, team_id):
	'''
	Get information on the team we're matched up against in the given round (od_round)

	:param str od_round: The round to get the match from, can be a num 1-10
	:param str team_id: The ID of the team on battlefy that we're grabbing a match for
	:return: a dict with information about the enemy team
	'''
	# get the match link
	match = await get_match(od_round)
	match_link = match_link_base.format(match['stageID'], match['_id'])
	
	# get the info about the team
	team_info = None
	for key in ['top', 'bottom']:
		team_id = get_team_id(match[key])
		if team_id != fwb_id:
			team_info = await get_team_info(team_id)

	team_info['match_link'] = match_link
	return team_info

#print(asyncio.get_event_loop().run_until_complete(get_other_team_info(9)))

import aiohttp
import pybuff

team_link = 'https://dtmwra1jsgyb0.cloudfront.net/persistent-teams/'
match_link_base = 'https://battlefy.com/overwatch-open-division-north-america/2018-overwatch-open-division-season-3' \
                  '-north-america/5b5e98399a8f8503cd0a07fd/stage/{}/match/{} '


class LinkNotFound(Exception):
        """Raised when an important link gives a status code other than 200"""


async def get_player_info(player_json, owner=False):
    user = player_json['user'] if not owner else player_json

    player_info = {'name': user['username']}

    battletag = ''
    try:
        battletag = user['inGameName']
    except KeyError:
        try:
            battletag = user['accounts']['battlenet']['battletag']
        except KeyError:
            pass
        
    try:
        player_info['info'] = await pybuff.get_player(battletag)
    except:
        player_info['info'] = None

    return player_info


async def get_team_info(persistent_team_id):
    curr_link = team_link + persistent_team_id
    team_info = None
    async with aiohttp.request('GET', curr_link) as request:
        if request.status == 200:
            data = await request.json()
            data = data[0]

            team_info = {
                'name': data['name'],
                'logo': data['logoUrl']
            }
            # team_info['link'] = 'https://battlefy.com/teams/' + persistent_team_id

            players = [await get_player_info(player) for player in data['persistentPlayers']]
            players.insert(0, await get_player_info(data['owner'], owner=True))
            team_info['players'] = players
            
            average_sr = 0
            player_total = 0
            for player in players:
                if player['info']:
                    sr = player['info'].get_sr()
                    if sr:
                        if sr > 0:
                            average_sr += sr
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
    except KeyError:
        return None


async def get_match(od_round, team_id):
    """
    Looks through all of the matches in od_round and returns the one with the given persistentTeamID
    :param str od_round: The round to get the match from, can be a num 1-10
    :param str team_id: The ID of the team on battlefy that we're grabbing a match for
    :return: A match dict or None if the match couldn't be found
    """

    matches = 'https://dtmwra1jsgyb0.cloudfront.net/stages/5b74a1b106dda6039a96e712/rounds/{}/matches'.format(od_round)

    async with aiohttp.request('GET', matches) as request:
        if request.status == 404:
            raise LinkNotFound(f"Unable to get match in round {od_round}.")

        matches_json = await request.json()

        for match in matches_json:
            for key in ['top', 'bottom']:
                if get_team_id(match[key]) == team_id:
                    return match


async def get_other_team_info(od_round, team_id):
    """
    Get information on the team we're matched up against in the given round (od_round)

    :param str od_round: The round to get the match from, can be a num 1-10
    :param str team_id: The ID of the team on battlefy that we're grabbing a match for
    :return: a dict with information about the enemy team
    """
    # get the match link
    match = await get_match(od_round, team_id)
    match_link = match_link_base.format(match['stageID'], match['_id'])
    
    # get the info about the team
    team_info = None
    for key in ['top', 'bottom']:
        current_team_id = get_team_id(match[key])
        if current_team_id != team_id:
            team_info = await get_team_info(current_team_id)

    team_info['match_link'] = match_link
    return team_info

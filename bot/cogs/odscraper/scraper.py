from aiohttp import ClientSession
from pybuff import get_player, BadBattletag
from typing import Dict, List


class LinkNotFound(Exception):
        """Raised when an important link gives a status code other than 200"""


async def get_player_info(active_ids: List[str], player_json: dict, session: ClientSession, owner=False) -> dict:
    user = player_json['user'] if not owner else player_json

    _id = player_json['_id']
    active = False
    if _id in active_ids:
        active_ids.remove(_id)
        active = True

    player_info = {'name': user['username'], 'active': active}

    battletag = ''
    try:
        battletag = user['inGameName']
    except KeyError:
        try:
            battletag = user['accounts']['battlenet']['battletag']
        except KeyError:
            pass
        
    try:
        player_info['info'] = await get_player(battletag, session=session)
    except BadBattletag:
        player_info['info'] = None

    return player_info


async def get_team_info(match: Dict, session: ClientSession) -> dict or str:
    team_link = 'https://dtmwra1jsgyb0.cloudfront.net/persistent-teams/'
    team = match[match['pos']]
    curr_link = team_link + get_team_id(team)
    async with session.get(curr_link) as request:
        if request.status == 200:
            data = await request.json()
        elif request.status == 404:
            raise LinkNotFound("Team not found on Battlefy.")
        else:
            return str(request.status)

    data = data[0]

    team_info = {
        'name': data['name'],
        'logo': data['logoUrl']
    }
    team = team['team']
    active_ids = [list(filter(lambda x: x['_id'] == _id, team['players']))[0]['persistentPlayerID'] for _id in team['playerIDs']]

    players = [await get_player_info(active_ids, player, session) for player in data['persistentPlayers']]
    players.insert(0, await get_player_info(active_ids, data['owner'], session, owner=True))
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

    return team_info


def get_team_id(team):
    # try here because apparently there can be matches where one of the teams just doesnt exist
    try:
        return team['team']['persistentTeamID']
    except KeyError:
        return None


async def get_match(stage_id: str, od_round: str, team_id: str, session: ClientSession) -> Dict or None:
    """
    Looks through all of the matches in od_round and returns the one with the given persistentTeamID

    :param str stage_id: stage ID to get matches for a round
    :param str od_round: The round to get the match from, can be a num 1-10
    :param str team_id: The ID of the team on battlefy that we're grabbing a match for
    :param ClientSession session: an aiohttp session, passing it makes stuff faster
    :return: A match dict or None if the match couldn't be found
    """

    matches = f'https://dtmwra1jsgyb0.cloudfront.net/stages/{stage_id}/rounds/{od_round}/matches'

    async with session.get(matches) as request:
        if request.status == 404:
            raise LinkNotFound(f"Unable to get match in round {od_round}.")

        matches_json = await request.json()
        if not matches_json:
            return

        found_match = None
        pos = ''
        positions = ['top', 'bottom']
        for match in matches_json:
            for key in positions:
                if get_team_id(match[key]) == team_id:
                    found_match = match
                    pos = positions[positions.index(key) - 1]
                    break

        if found_match:
            async with session.get(f"https://dtmwra1jsgyb0.cloudfront.net/matches/{found_match['_id']}"
                                   f"?extend[{pos}.team][players][users]") as r:
                match_json = await r.json()
            match_json = match_json[0]
            match_json['pos'] = pos
            return match_json


async def get_other_team_info(stage_id: str, od_round: str, team_id: str) -> Dict or None:
    """
    Get information on the team we're matched up against in the given round (od_round)

    :param str stage_id: stage id from the tournament link
    :param str od_round: The round to get the match from, can be a num 1-10
    :param str team_id: The ID of the team on battlefy that we're grabbing a match for
    :return: a dict with information about the enemy team
    """

    session = ClientSession()

    # TODO: Save tournament URL in !set_tourney and pass it here because this URL is wrong lmao
    match_link_base = 'https://battlefy.com/overwatch-open-division-north-america/2018-overwatch-open-division-season' \
                      '-3-north-america/5b5e98399a8f8503cd0a07fd/stage/{}/match/{} '

    # get the match link
    match = await get_match(stage_id, od_round, team_id, session)
    if not match:
        await session.close()
        return
    match_link = match_link_base.format(match['stageID'], match['_id'])
    
    # get the info about the team
    team_info = await get_team_info(match, session)

    await session.close()

    team_info['match_link'] = match_link
    return team_info

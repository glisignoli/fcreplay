from datetime import timedelta
from fcreplay.config import Config
from fcreplay.database import Database
from fcreplay.status import status
from retrying import retry
import datetime
import json
import logging
import pkg_resources
import re
import requests

log = logging.getLogger('fcreplay')


class Getreplay:
    """Classmethod to getreplay."""

    def __init__(self):
        """Initialize the Getreplay class."""
        self.config = Config()
        self.db = Database()

        with open(pkg_resources.resource_filename('fcreplay', 'data/supported_games.json')) as f:
            self.supported_games = json.load(f)

    @retry(wait_random_min=5000, wait_random_max=10000, stop_max_attempt_number=3)
    def get_data(self, query):
        """Get data from fightcade api.

        Args:
            query (dict): Query to pass to fightcade API

        Raises:
            IOError: Rase error when unable to get data or status code == 500

        Returns:
            dict: Returns dict containting the request Eg:
            {
                "results": {
                    "results": [
                        {
                            "quarkid": "12341234121234-1234",
                            "channelname": "Full channel name",
                            "date": 1659855001234,
                            "duration": 123.066,
                            "emulator": "fbneo",
                            "gameid": "rom_name",
                            "num_matches": 2,
                            "players": [
                                {
                                    "name": "Player1 Name",
                                    "country": "US",
                                    "rank": 2,
                                    "score": 0
                                },
                                {
                                    "name": "Player2 Name",
                                    "country": "US",
                                    "rank": 3,
                                    "score": 2
                                }
                            ],
                            "ranked": 3,
                            "replay_file": "12341234121234-1234-replay.fs"
                        }
                    ],
                    "count": 15
                },
                "res": "OK"
            }
        """

        r = requests.post(
            "https://www.fightcade.com/api/",
            json=query
        )
        if r.status_code == 500:
            log.error("500 Code, trying up to 3 times")
            raise IOError("Unable to get data")
        else:
            return r.json()

    def check_banned_user(self, player):
        """Check if player is banned.

        Args:
            player (str): Player to check

        Returns:
            bool: Returns True if player is banned, False if not
        """
        if player in self.config.banned_users:
            return True
        else:
            return False

    def add_replay(self, replay, emulator, game, player_replay=True):
        """Add replay to the database.

        Args:
            replay ([type]): [description]
            emulator ([type]): [description]
            game ([type]): [description]
            player_replay (bool, optional): [description]. Defaults to True.
        """
        challenge_id = replay['quarkid']
        p1_loc = replay['players'][0]['country']
        p2_loc = replay['players'][1]['country']
        p1 = replay['players'][0]['name']
        p2 = replay['players'][1]['name']
        date_replay = datetime.datetime.fromtimestamp(replay['date'] // 1000)
        length = replay['duration']
        created = False
        failed = False
        local_status = status.ADDED
        date_added = datetime.datetime.utcnow()
        player_requested = player_replay
        fail_count = 0

        # Check if player is banned:
        for p in replay['players']:
            if p['name'] in self.config.banned_users:
                return status.BANNED_USER

        if 'rank' in replay['players'] or 'rank' in replay['players'][1]:
            if replay['players'][0]['rank'] is None:
                p1_rank = '0'
            else:
                p1_rank = replay['players'][0]['rank']
            if replay['players'][1]['rank'] is None:
                p2_rank = '0'
            else:
                p2_rank = replay['players'][1]['rank']
        else:
            p1_rank = '0'
            p2_rank = '0'

        # Insert into database
        log.info(f"Looking for {challenge_id}")

        # Check if replay exists
        data = self.db.get_single_replay(challenge_id=challenge_id)
        if data is None:
            # Limit the length of videos
            if length > int(self.config.min_replay_length) and \
               length < int(self.config.max_replay_length):
                log.info(f"Adding {challenge_id} to queue")
                self.db.add_replay(
                    challenge_id=challenge_id,
                    p1_loc=p1_loc,
                    p2_loc=p2_loc,
                    p1_rank=p1_rank,
                    p2_rank=p2_rank,
                    p1=p1,
                    p2=p2,
                    date_replay=date_replay,
                    length=length,
                    created=created,
                    failed=failed,
                    status=local_status,
                    date_added=date_added,
                    player_requested=player_requested,
                    game=game,
                    emulator=emulator,
                    video_processed=False,
                    fail_count=fail_count
                )
                return(status.ADDED)
            else:
                log.info(f"{challenge_id} is only {length} not adding")
                if player_replay:
                    return(status.TOO_SHORT)
        else:
            log.info(f"{challenge_id} already exists")
            if player_replay:
                # Check if the returned replay is a player replay
                if data.player_requested:
                    return(status.ALREADY_EXISTS)
                else:
                    # Update DB to mark returned replay as player replay
                    self.db.update_player_requested(challenge_id=challenge_id)
                    return(status.MARKED_PLAYER)
            return(status.ALREADY_EXISTS)

    def get_game_replays(self, game):
        """Get a list of games for a game.

        Args:
            game (str): Game id to use
        """
        if game not in self.supported_games:
            return(status.UNSUPPORTED_GAME)

        query = {'req': 'searchquarks', 'gameid': game}

        r = self.get_data(query)

        for i in r['results']['results']:
            if i['emulator'] == 'fbneo' and i['live'] is False:
                local_status = self.add_replay(
                    replay=i,
                    emulator=i['emulator'],
                    game=game,
                    player_replay=False
                )
                if local_status != status.ADDED:
                    log.info(f'Not adding game, Status: {local_status}')

        return(status.ADDED)

    def get_top_weekly(self):
        """Get the most recent games and add them to the database.

        Returns:
            str: Returns the status of the request
        """
        today = datetime.datetime.today()
        start_week = today - timedelta(days=today.weekday())
        start_week_ms = int(start_week.timestamp() * 1000)
        query = {'req': 'searchquarks', 'best': True, 'since': start_week_ms}

        replays = []
        pages = self.config.get_weekly_replay_pages
        for i in range(0, pages):
            query['offset'] = i * 15
            r = self.get_data(query)
            replays += r['results']['results']

        for i in replays:
            if i['gameid'] not in self.supported_games:
                log.info(f"Game {i['gameid']} not supported for replay {i['quarkid']}")
                continue
            local_status = self.add_replay(
                replay=i,
                emulator=i['emulator'],
                game=i['gameid'],
                player_replay=False
            )
            if local_status != status.ADDED:
                log.info(f"Not adding replay {i['quarkid']}, Status: {local_status}")

        return status.ADDED

    def get_ranked_replays(self, game, username=None, pages=None):
        """Get a list of ranked games for a game and add them to the database.

        Args:
            game (str): Game id
            username (username, optional): Username. Defaults to None.
            pages (int, optional): Number of pages to search. Defaults to None.

        Returns:
            str: Returns the status of the request
        """
        if game not in self.supported_games:
            return(status.UNSUPPORTED_GAME)

        query = {"req": "searchquarks", "best": True, "gameid": game}

        if username is not None:
            query['username'] = username

        replays = []
        if pages is None:
            query['offset'] = 0
            r = self.get_data(query)
            replays += r['results']['results']
        else:
            for page in range(0, pages):
                query['offset'] = page
                r = self.get_data(query)
                replays += r['results']['results']

        for i in replays:
            if i['emulator'] == 'fbneo' and i['live'] is False:
                local_status = self.add_replay(
                    replay=i,
                    emulator=i['emulator'],
                    game=game,
                    player_replay=False
                )
                if local_status != status.ADDED:
                    log.info(f'Not adding game, Status: {local_status}')

        return status.ADDED

    def get_replay(self, url, player_requested=False):
        """Get a replay by url.

        Args:
            url (str): Url to retrieve the replay from
            player_requested (bool, optional): Is this a player requested replay. Defaults to False.

        Returns:
            str: Returns the string status of the request
        """
        # Validate url, this could probably be done better
        pattern = re.compile(r'^https://replay\.fightcade\.com/fbneo/.*/[0-9]*-[0-9]*$')
        if not pattern.match(url):
            return(status.INVALID_URL)

        # Parse url
        emulator = url.split('/')[3]
        game = url.split('/')[4]
        challenge_id = url.split('/')[5]
        log.debug(f"Parsed url: emulator: {emulator}, game: {game}, challenge_id: {challenge_id}")

        if game not in self.supported_games:
            return(status.UNSUPPORTED_GAME)

        # Get play replays
        query = {
            "req": "searchquarks",
            "quarkid": challenge_id
        }
        r = self.get_data(query)

        # Look for replay in results
        for i in r['results']['results']:
            if challenge_id == i['quarkid']:
                return self.add_replay(
                    replay=i,
                    emulator=emulator,
                    game=game,
                    player_replay=player_requested
                )
        return status.REPLAY_NOT_FOUND

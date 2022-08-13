"""Test for the fcreplay .

Returns:
    [type]: [description]
"""

from fcreplay.getreplay import Getreplay
from fcreplay.database import Database
from fcreplay.status import status
import sys
from unittest.mock import patch, MagicMock

sys.modules['pyautogui'] = MagicMock()


class FixtureDatabase(Database):
    """Classmethod to test a database."""

    def __init__(self):
        """__init__ method."""
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from fcreplay.models import Base

        engine = create_engine("sqlite+pysqlite:///:memory:", echo=False, future=True)
        Base.metadata.create_all(engine)
        self.Session = sessionmaker(bind=engine)
        self.session = self.Session()


class TestGetreplay:
    """Test."""

    # @patch('debugpy.wait_for_client')
    # @patch('debugpy.listen')
    # def setUp(self, mock_debugpy_listen, mock_debugpy_wait_for_client):
    #     """Setup."""
    #     with patch.dict('os.environ', {'REMOTE_DEBUG': 'True'}):
    #         getreplay = Getreplay()
    #         assert mock_debugpy_listen.called
    #         assert mock_debugpy_wait_for_client.called
    #         return getreplay

    def test_get_date(self):
        """test_get_date method."""
        pass

    @patch('fcreplay.getreplay.Config')
    def test_add_replay(self, mock_config):
        """test_add_replay method.

        Args:
            mock_cofig (MqgicMock): config mock.
        """

        with patch.object(Getreplay, '__init__', return_value=None):
            g = Getreplay()
            g.db = FixtureDatabase()
            g.config = mock_config

        g.config.min_replay_length = 0
        g.config.max_replay_length = 123456789

        r = {
            "quarkid": "12341234121234-1111",
            "channelname": "Full channel name",
            "date": 1659855001234,
            "duration": 12345.6789,
            "emulator": "fbneo",
            "gameid": "rom_name",
            "num_matches": 2,
            "players": [
                {
                    "name": "BannedPlayer1",
                    "country": "US",
                    "rank": 2,
                    "score": 0
                },
                {
                    "name": "BannedPlayer2",
                    "country": "US",
                    "rank": 3,
                    "score": 2
                }
            ],
            "ranked": 3,
            "replay_file": "12341234121234-1234-replay.fs"
        }

        # Add replay to database
        assert g.add_replay(
            replay=r,
            emulator="fbneo",
            game="rom_name",
            player_replay=True
        ) == status.ADDED, "Should return status.ADDED"

        # Test bannded players and additional replays
        g.config.banned_players = ["BannedPlayer1"]
        r["quarkid"] = "12341234121234-2222",
        assert g.add_replay(
            replay=r,
            emulator="fbneo",
            game="rom_name",
            player_replay=True
        ) == status.BANNED_USER, "Should return status.BANNED_USER when player 1 is banned"

        g.config.banned_players = ["BannedPlayer2"]
        r["quarkid"] = "12341234121234-3333",
        assert g.add_replay(
            replay=r,
            emulator="fbneo",
            game="rom_name",
            player_replay=True
        ) == status.BANNED_USER, "Should return status.BANNED_USER when player 2 is banned"

        g.config.banned_players = ["BannedPlayer1", "BannedPlayer2"]
        r["quarkid"] = "12341234121234-4444",
        assert g.add_replay(
            replay=r,
            emulator="fbneo",
            game="rom_name",
            player_replay=True
        ) == status.BANNED_USER, "Should return status.BANNED_USER when when both players are banned"

    def get_game_replays(self):
        pass

    def get_top_weekly(self):
        pass

    def get_ranked_replays(self):
        pass

    def get_replay(self):
        pass

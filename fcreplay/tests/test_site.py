"""Test Site."""
import os
os.environ['FCREPLAY_CONFIG'] = './fcreplay/tests/common/config_test_site.json'

from flask import session
from flask.testing import FlaskClient
from fcreplay.site.create_app import create_app, db
from fcreplay.site.site_config import TestConfig
from unittest.mock import patch, MagicMock
import xml.etree.ElementTree as ET
import pytest

class TestSite:
    """Test site."""

    @pytest.fixture
    def app(mocker):
        """Create a Flask app."""
        app = create_app(TestConfig)

        # Create Tables
        db.app = app
        db.create_all()

        yield app.test_client()

    def test_site_root(self, app: FlaskClient):
        """Test the site root."""
        rv = app.get('/')

        assert rv.status_code == 200

    def test_api_videolinks(self, app: FlaskClient):
        """Test the api for video links."""
        # Should return 404 when missing ids key missing
        rv = app.post('/api/videolinks', json={})
        assert rv.status_code == 404

        # Should return 200 when ids key present
        rv = app.post('/api/videolinks', json={
            'ids': [1, 2, 3]
        })
        assert rv.status_code == 200
        assert rv.is_json

    def test_api_supportedgames(self, app: FlaskClient):
        """Test the api for supported games."""
        rv = app.get('/api/supportedgames')

        assert rv.status_code == 200
        assert rv.is_json

    # # Need to mock getreplay.get_data
    # @patch('fcreplay.getreplay.requests')
    # @patch('fcreplay.getreplay.Config')
    # @patch('fcreplay.database.Config')
    # def test_submit(self, mock_config_db: MagicMock, mock_config_gr, mock_requests, app: FlaskClient):
    #     """Test the submit page."""
    #     # Need to test submissions for good data, bad data and banned players
    #     mock_sqlite_baseurl = MagicMock()
    #     mock_sqlite_baseurl.sql_baseurl = 'sqlite+pysqlite:///:memory:'

    #     mock_config_db.return_value = mock_sqlite_baseurl

    #     mock_config_gr_data = MagicMock()
    #     mock_config_gr_data.min_replay_length = 1
    #     mock_config_gr_data.max_replay_length = 1000

    #     mock_config_gr.return_value = mock_config_gr_data

    #     mock_requests.status_code = 200

    #     mock_post = MagicMock()
    #     mock_post.json.return_value = {
    #         "results": {
    #             "results": [
    #                 {
    #                     "quarkid": "1234567891234-1234",
    #                     "channelname": "Full channel name",
    #                     "date": 1659855001234,
    #                     "duration": 123.066,
    #                     "emulator": "fbneo",
    #                     "gameid": "rom_name",
    #                     "num_matches": 2,
    #                     "players": [
    #                         {
    #                             "name": "Player1 Name",
    #                             "country": "US",
    #                             "rank": 2,
    #                             "score": 0
    #                         },
    #                         {
    #                             "name": "Player2 Name",
    #                             "country": "US",
    #                             "rank": 3,
    #                             "score": 2
    #                         }
    #                     ],
    #                     "ranked": 3,
    #                     "replay_file": "12341234121234-1234-replay.fs"
    #                 }
    #             ],
    #             "count": 15
    #         },
    #         "res": "OK"
    #     }
    #     mock_requests.post.return_value = mock_post

    #     with app:
    #         rv = app.post('/submitResult', data={
    #             "challenge_url": "https://replay.fightcade.com/fbneo/sf2/1234567891234-1234"
    #         })

    #         assert session['replay_result'] == 'ADDED', 'Replay result should be ADDED'
    #         assert rv.status_code == 302, "Should return 302, redirect"

    #     with app:
    #         rv = app.post('/submitResult', data={
    #             "challenge_url": "not a url"
    #         })

    #         assert session['replay_result'] == 'INVALID_URL', 'Replay result should be INVALID_URL'
    #         assert rv.status_code == 302, "Should return 302, redirect"

    #     mock_post.json.return_value = {
    #         "results": {
    #             "results": [
    #                 {
    #                     "quarkid": "1234567891234-1234",
    #                     "channelname": "Full channel name",
    #                     "date": 1659855001234,
    #                     "duration": 123.066,
    #                     "emulator": "fbneo",
    #                     "gameid": "rom_name",
    #                     "num_matches": 2,
    #                     "players": [
    #                         {
    #                             "name": "BannedUser1",
    #                             "country": "US",
    #                             "rank": 2,
    #                             "score": 0
    #                         },
    #                         {
    #                             "name": "BannedUser2",
    #                             "country": "US",
    #                             "rank": 3,
    #                             "score": 2
    #                         }
    #                     ],
    #                     "ranked": 3,
    #                     "replay_file": "12341234121234-1234-replay.fs"
    #                 }
    #             ],
    #             "count": 15
    #         },
    #         "res": "OK"
    #     }
    #     mock_requests.post.return_value = mock_post

    #     with app:
    #         mock_config_gr_data.banned_users = ['BannedUser1']
    #         mock_config_gr.return_value = mock_config_gr_data

    #         rv = app.post('/submitResult', data={
    #             "challenge_url": "https://replay.fightcade.com/fbneo/sf2/1234567891234-1234"
    #         })

    #         assert session['replay_result'] == 'BANNED_USER', 'Replay result should be BANNED_USER'
    #         assert rv.status_code == 302, "Should return 302, redirect"

    #     with app:
    #         mock_config_gr_data.banned_users = ['BannedUser2']
    #         mock_config_gr.return_value = mock_config_gr_data

    #         rv = app.post('/submitResult', data={
    #             "challenge_url": "https://replay.fightcade.com/fbneo/sf2/1234567891234-1234"
    #         })

    #         assert session['replay_result'] == 'BANNED_USER', 'Replay result should be BANNED_USER'
    #         assert rv.status_code == 302, "Should return 302, redirect"

    # def test_submitResult(self, app: FlaskClient):
    #     """Test the submit page."""
    #     rv = app.get('/submit')

    #     assert rv.status_code == 200

    def test_assets(self, app: FlaskClient):
        pass

    def test_about(self, app: FlaskClient):
        """Test the about page."""
        rv = app.get('/about')

        assert rv.status_code == 200

    def test_advancedSearch(self, app: FlaskClient):
        pass

    def test_advancedSearchResult(self, app: FlaskClient):
        pass

    def test_search(self, app: FlaskClient):
        pass

    def test_robots_and_ads(self, app: FlaskClient):
        """Test the robots.txt and ads.txt."""
        rv_ads = app.get('/ads.txt')
        rv_robots = app.get('/robots.txt')

        assert rv_ads.status_code == 200
        assert rv_robots.status_code == 200

    def test_sitemap(self, app: FlaskClient):
        """Test the sitemap."""
        rv = app.get('/sitemap.xml')

        assert rv.status_code == 200
        assert ET.fromstring(rv.data)

        try:
            bad_xml = "foo"
            ET.fromstring(bad_xml)
            assert False, "Bad xml should have thrown an exception"
        except ET.ParseError:
            assert True

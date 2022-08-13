import os
os.environ['FCREPLAY_CONFIG'] = './fcreplay/tests/common/config_test_site.json'

from fcreplay.site.create_app import create_app, db
from fcreplay.site.site_config import TestConfig
import xml.etree.ElementTree as ET
import pytest

class TestSite:
    @pytest.fixture
    def app(self):
        app = create_app(TestConfig)

        # Create Tables
        db.app = app
        db.create_all()

        yield app.test_client()

    def test_site_root(self, app):
        rv = app.get('/')

        assert rv.status_code == 200

    def test_api_videolinks(self, app):
        # Should return 404 when missing ids key missing
        rv = app.post('/api/videolinks', json={})
        assert rv.status_code == 404

        # Should return 200 when ids key present
        rv = app.post('/api/videolinks', json={
            'ids': [1, 2, 3]
        })
        assert rv.status_code == 200
        assert rv.is_json

    def test_api_supportedgames(self, app):
        rv = app.get('/api/supportedgames')

        assert rv.status_code == 200
        assert rv.is_json

    def test_submit(self, app):
        pass

    def test_submitResult(self, app):
        pass

    def test_assets(self, app):
        pass

    def test_about(self, app):
        rv = app.get('/about')

        assert rv.status_code == 200

    def test_advancedSearch(self, app):
        pass

    def test_advancedSearchResult(self, app):
        pass

    def test_search(self, app):
        
        pass

    def test_robots_and_ads(self, app):
        rv_ads = app.get('/ads.txt')
        rv_robots = app.get('/robots.txt')

        assert rv_ads.status_code == 200
        assert rv_robots.status_code == 200

    def test_sitemap(self, app):
        rv = app.get('/sitemap.xml')

        assert rv.status_code == 200
        assert ET.fromstring(rv.data)

        try:
            bad_xml = "foo"
            ET.fromstring(bad_xml)
            assert False, "Bad xml should have thrown an exception"
        except ET.ParseError:
            assert True

from fcreplay.config import Config as FcreplayConfig


class Config(object):
    config = FcreplayConfig()
    DEBUG = False
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_DATABASE_URI = config.sql_baseurl
    SECRET_KEY = config.secret_key


class ProdConfig(Config):
    config = FcreplayConfig()
    ENV = 'prod'


class DevConfig(Config):
    ENV = 'dev'
    DEBUG = True

class TestConfig(Config):
    config = FcreplayConfig()

    TESTING = True
    DEBUG = True

    SQLALCHEMY_DATABASE_URI = 'sqlite://'
    SECRET_KEY = 'testingtestingtesting'

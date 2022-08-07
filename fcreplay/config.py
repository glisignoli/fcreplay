from cerberus import Validator
import base64
import json
import os
import sys


class Config:
    """ Configuration class.
    This class is used to load and validate the configuration file.
    """

    def __init__(self):
        self.description_append_file: str = str()
        "Append file"

        self.fcadefbneo_path: str = str()
        "Path to the fcadedbneo executable"

        self.fcreplay_dir: str = str()
        "Path to the fcreplay directory"

        self.get_weekly_replay_pages: int = int()
        "Number of pages to get from the fcadedbneo website"

        self.ia_settings: dict = dict()
        "Settings for the IA"

        self.kill_all: bool = bool()
        "Kill all running instances of fcadedbneo"

        self.logging_loki: dict = dict()
        "Logging settings for loki"

        self.logfile: str = str()
        "Logfile path"

        self.loglevel: str = str()
        "Logging level"

        self.min_replay_length: int = int()
        "Minimum length of a replay"

        self.max_replay_length: int = int()
        "Maximum length of a replay"

        self.player_replay_first: bool = bool()
        "If true, player replays will be encoded first"

        self.random_replay: bool = bool()
        "If true, a random replay will be selected"

        self.record_timeout: int = int()
        "Timeout for the record command"

        self.resolution: list = list()
        "Resolution for the replay"

        self.remove_old_avi_files: bool = bool()
        "If true, old avi files will be removed"

        self.secret_key: str = str()
        "Secret key for the flask app"

        self.sql_baseurl: str = str()
        "Base url for the sql database"

        self.upload_to_ia: bool = bool()
        "If true, replays will be uploaded to the IA"

        self.upload_to_yt: bool = bool()
        "If true, replays will be uploaded to the youtube"

        self.youtube_credentials: str = str()
        "Path to the youtube credentials file"

        self.youtube_max_daily_uploads: int = int()
        "Maximum number of daily youtube uploads"

        self.youtube_secrets: str = str()
        "Path to the youtube secrets file"

        self.bad_words_file: str = str()
        "Path to the bad words file"

        self.opentelemetry_config: dict = dict()
        "Opentelemetry config"

        c = self._validate_config()

        # Load the config into the class variables
        for k in c:
            if k not in self.__dict__:
                print(f"Invalid config key: {k}")
                sys.exit(1)
            else:
                setattr(self, k, c[k])

    def _validate_config(self) -> dict:
        """ Private function to validate config
        """
        self.schema = {
            'description_append_file': {
                'type': 'list',
                'required': True,
                'meta': {
                    'description': "Enable description to be appended from file",
                    'default': [False, '/root/description_file.txt'],
                }
            },
            'fcadefbneo_path': {
                'type': 'string',
                'required': True,
                'meta': {
                    'default': '/Fightcade/emulator/fbneo',
                    'description': 'Path to fcadefbneo'
                },
            },
            'fcreplay_dir': {
                'type': 'string',
                'required': True,
                'meta': {
                    'default': '/root',
                    'description': 'Path of where to run fcreplay',
                }
            },
            'get_weekly_replay_pages': {
                'type': 'number',
                'meta': {
                    'default': 1,
                    'description': 'Number of replay pages to get for weekly replays'
                }
            },
            'ia_settings': {
                'type': 'dict',
                'required': False,
                'schema': {
                    'collection': {
                        'type': 'string',
                        'required': True,
                    },
                    'creator': {
                        'type': 'string',
                        'required': True,
                    },
                    'language': {
                        'type': 'string',
                        'required': True
                    },
                    'license_url': {
                        'type': 'string',
                        'required': True,
                    },
                    'mediatype': {
                        'type': 'string',
                        'required': True,
                    },
                    'subject': {
                        'type': 'list',
                        'required': True
                    }
                },
                'meta': {
                    'default': {
                        "collection": "Collection-Name",
                        "creator": "Author",
                        "language": "Language",
                        "license_url": "http://creativecommons.org/publicdomain/zero/1.0",
                        "mediatype": "video",
                        "subject": ["video", "fightcade"]
                    },
                    'description': 'Dictionary of Internet Archive settings'
                }
            },
            'kill_all': {
                'type': 'boolean',
                'required': True,
                'meta': {
                    'default': False,
                    'description': 'Kill all running processes on failure, useful for docker containers'
                }
            },
            'logging_loki': {
                'type': 'dict',
                'required': True,
                'meta': {
                    'default': {
                        'enabled': False,
                        'password': 'password',
                        'url': 'https://my-loki-instance:1234/loki/api/v1/push',
                        'username': 'username'
                    },
                    'description': 'Enables logging to a loki endpoint'
                }
            },
            'logfile': {
                'type': 'string',
                'meta': {
                    'default': '/home/fcrecorder/fcreplay/fcreplay.log',
                    'description': 'Path of where to write log file',
                }
            },
            'loglevel': {
                'type': 'string',
                'allowed': ['ERROR', 'INFO', 'DEBUG'],
                'required': True,
                'meta': {
                    'default': 'INFO',
                    'description': 'Log level',
                }
            },
            'max_replay_length': {
                'type': 'number',
                'required': True,
                'meta': {
                    'default': 10800,
                    'description': 'Maximum replay length to accept in seconds',
                }
            },
            'min_replay_length': {
                'type': 'number',
                'required': True,
                'meta': {
                    'default': 60,
                    'description': 'Minimum replay length to accept in seconds',
                }
            },
            'player_replay_first': {
                'type': 'boolean',
                'required': True,
                'meta': {
                    'default': True,
                    'description': 'Look for player replay to record first',
                }
            },
            'random_replay': {
                'type': 'boolean',
                'required': True,
                'meta': {
                    'default': False,
                    'description': 'Encode a random replay, otherwise encode the oldest'
                }
            },
            'record_timeout': {
                'type': 'number',
                'required': True,
                'meta': {
                    'default': 120,
                    'description': 'Time in seconds before marking a replay as failed if start not detected'
                }
            },
            'resolution': {
                'type': 'list',
                'required': True,
                'meta': {
                    'default': [1920, 1080],
                    'description': 'Resolution for the replay'
                }
            },
            'remove_old_avi_files': {
                'type': 'boolean',
                'required': True,
                'meta': {
                    'default': True,
                    'description': 'Remove old raw avi files.'
                }
            },
            'secret_key': {
                'type': 'string',
                'required': True,
                'meta': {
                    'default': base64.b64encode(os.urandom(64)).decode(),
                    'description': 'Secret key used for flask/site cookies'
                }
            },
            'sql_baseurl': {
                'type': 'string',
                'required': True,
                'meta': {
                    'default': 'postgres://username:password@postgres:5432',
                    'description': 'URL of database'
                }
            },
            'upload_to_ia': {
                'type': 'boolean',
                'required': True,
                'meta': {
                    'default': False,
                    'description': 'Upload replay to Internet Archive'
                }
            },
            'upload_to_yt': {
                'type': 'boolean',
                'required': True,
                'meta': {
                    'default': False,
                    'description': 'Upload replays to Youtube'
                }
            },
            'youtube_credentials': {
                'type': 'string',
                'meta': {
                    'default': '/root/.youtube-upload-credentials.json',
                    'description': 'Path to youtube-upload-credentials.json file'
                }
            },
            'youtube_max_daily_uploads': {
                'type': 'number',
                'meta': {
                    'default': 5,
                    'description': 'Maximum number of uploads to youtube per day'
                }
            },
            'youtube_secrets': {
                'type': 'string',
                'meta': {
                    'default': '/root/.youtube-secrets.json',
                    'description': 'Path to youtube-secrets.json file'
                }
            },
            'bad_words_file': {
                'type': 'string',
                'required': True,
                'meta': {
                    'default': '/home/fcrecorder/fcreplay/bad_words.txt',
                    'description': 'Path to bad words file',
                }
            },
            'opentelemetry_config': {
                'type': 'dict',
                'required': False,
                'meta': {
                    'default': {
                        'enabled': False,
                        'description': 'Opentelemetry configuration'
                    }
                },
                'schema': {
                    'enabled': {
                        'type': 'boolean',
                        'required': False,
                    },
                    'endpoint': {
                        'type': 'string',
                        'required': False,
                    },
                    'secure': {
                        'type': 'boolean',
                        'required': False,
                    },
                    'headers': {
                        'type': 'dict',
                        'required': False,
                    }
                }
            }
        }
        self._config = self._get_config()
        self.validate_config(self._config, self.schema)

        return self._config

    def _get_config(self) -> dict:
        """Get config from file or from the FCREPLAY_CONFIG environment variable.

        Returns:
            dict Config dictionary
        """
        try:
            if 'FCREPLAY_CONFIG' in os.environ:
                with open(os.environ['FCREPLAY_CONFIG'], 'r') as json_data_file:
                    return json.load(json_data_file)
            else:
                with open("config.json", 'r') as json_data_file:
                    return json.load(json_data_file)

        except FileNotFoundError:
            print("Unable to find config file, please generate one using `fcreplay config generate`")
            sys.exit(1)

    def validate_config(self, config, schema):
        v = Validator()
        if v.validate(config, schema) is False:
            print(json.dumps(v.errors, indent=4))
            print("\nConfig is invalid. Please fix the above errors")
            sys.exit(1)
        else:
            return True

    def validate_config_file(self, config_file):
        with open(config_file) as f:
            if self.validate_config(json.load(f), self.schema):
                print('Config file is valid')

    def generate_config(self):
        default_json = {}
        for k in self.schema:
            if 'default' in self.schema[k]['meta']:
                default_json[k] = self.schema[k]['meta']['default']

        print(json.dumps(default_json, indent=4))

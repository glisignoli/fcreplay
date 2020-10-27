from flask import Flask
from flask_bootstrap import Bootstrap
from flask_cors import CORS

from fcreplay.site.filters import convertLength, linkPath
from fcreplay.site.blueprint import app as blueprint_app
from fcreplay.site.database import db

import os


def create_app(app_config):
    if 'REMOTE_DEBUG' in os.environ:
        import debugpy
        debugpy.listen(("0.0.0.0", 5678))
        debugpy.wait_for_client()

    #app = Flask(__name__, static_folder='static')
    app = Flask(__name__)

    # Get flask config from object
    app.config.from_object(app_config)

    # Initalise Database
    db.init_app(app)

    # Initalise Jinija2 Filters
    app_filters(app)

    # Register blueprint
    app.register_blueprint(blueprint_app)

    # Add flask_bootstrap
    Bootstrap(app)

    # Cors
    cors(app)

    return app


def app_filters(app):
    app.jinja_env.filters['convertLenth'] = convertLength
    app.jinja_env.filters['linkPath'] = linkPath


def cors(app):
    cors = CORS(app, resources={r"/api/*": {"origins": "*"}})
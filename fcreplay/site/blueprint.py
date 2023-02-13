from fcreplay.site import queries
from fcreplay.site.database import db
from fcreplay.site.forms import AdvancedSearchForm, SearchForm, SubmitForm
from fcreplay.site.feed import Feed

from flask import Blueprint
from flask import abort, jsonify, render_template, request, session, redirect, send_from_directory, url_for

import datetime
import json
import logging
import pkg_resources
import pytz

app = Blueprint('blueprint', __name__, static_folder='static')

with open(pkg_resources.resource_filename('fcreplay', 'data/supported_games.json')) as f:
    supported_games = json.load(f)


@app.route('/')
def index():
    searchForm = SearchForm()
    page = request.args.get('page', 1, type=int)
    pagination = queries.all_replays().paginate(page, per_page=9)
    replays = pagination.items

    return render_template('start.j2.html', pagination=pagination, replays=replays, form=searchForm, games=supported_games)


@app.route('/api/videolinks', methods=['POST'])
def videolinks():
    if 'ids' not in request.json:
        abort(404)

    replays = queries.multiple_replays(request.json['ids'])

    replay_data = {}
    for i in replays:
        replay_data[i.id] = f"https://fightcadevids.com/video/{i.id}"

    return jsonify(replay_data)


@app.route('/api/supportedgames')
def supportedgames():
    return jsonify(supported_games)


@app.route('/api/playerlist')
def playerList():
    playerlist = queries.playerlist()
    playerlist = sorted(playerlist)
    return jsonify(playerlist)


@app.route('/api/playerlist/search', methods=['POST'])
def playerListSearch():
    if 'player_id' not in request.json:
        abort(404)
    playerlist = queries.playerlist_search(request.json['player_id'])
    playerlist = sorted(playerlist)
    return jsonify(playerlist)


# @app.route('/submit')
# def submit():
#     searchForm = SearchForm()
#     submitForm = SubmitForm()
#    return render_template('submit.j2.html', form=searchForm, submitForm=submitForm, submit_active=True)


# @app.route('/submitResult', methods=['POST', 'GET'])
# def submitResult():
#     logging.debug(f"Session: {session}")
#     # I feel like there should be a better way to do this
#     if request.method == 'POST':
#         result = SubmitForm(request.form)

#         challenge_id = result.challenge_url.data
#         session['challenge_url'] = result.challenge_url.data

#         from fcreplay.getreplay import Getreplay
#         replay_result = Getreplay().get_replay(challenge_id, player_requested=True)

#         session['replay_result'] = replay_result
#         logging.info(f"Submit replay: {challenge_id} status is: {replay_result}")

#         # Add replay and get status here
#         return redirect(url_for('blueprint.submitResult'))
#     else:
#         searchForm = SearchForm()
#         if 'replay_result' not in session:
#             return index()
#         result = session['replay_result']
#         return render_template('submitResult.j2.html', form=searchForm, result=result, submt_active=True)


@app.route('/search/assets/<path:path>')
@app.route('/assets/<path:path>')
def send_js(path):
    return send_from_directory('templates/assets', path)


@app.route('/about')
def about():
    searchForm = SearchForm()

    sortedGames = sorted(supported_games.items(), key=lambda item: item[1]['game_name'])
    supportedGames = {}
    for game in sortedGames:
        supportedGames[game[0]] = {
            'game_name': supported_games[game[0]]['game_name'],
        }
        supportedGames[game[0]]['count'] = db.session.execute(f"select count(id) from replays where created = true and game = '{game[0]}'").first()[0]

    numberOfReplays = db.session.execute('select count(id) from replays where created = true').first()[0]

    toProcess = db.session.execute('select count(id) from replays where created = false and failed = false').first()[0]

    return render_template('about.j2.html', about_active=True, form=searchForm, supportedGames=supportedGames, numberOfReplays=numberOfReplays, toProcess=toProcess)


@app.route('/advancedSearch')
def advancedSearch():
    searchForm = SearchForm()
    advancedSearchForm = AdvancedSearchForm()

    all_characters_sql = db.session.execute('select p1_char as char,game from character_detect union select p2_char as char,game from character_detect')
    all_characters_dict = {}

    for row in all_characters_sql:
        if row.game not in all_characters_dict:
            all_characters_dict[row.game] = []
        all_characters_dict[row.game].append(row.char)

    players_list = queries.playerlist()
    players_list = sorted(players_list)

    advancedSearchForm.p1_name.choices = players_list
    advancedSearchForm.p2_name.choices = players_list

    return render_template('advancedSearch.j2.html', advancedsearch_active=True, form=searchForm, advancedSearchForm=advancedSearchForm, character_dict=all_characters_dict, players_list=players_list)


@app.route('/advancedSearchResult')
def advancedSearchResult():
    search = request.args.get('search')
    p1_name = request.args.get('p1_name', default='', type=str)
    p2_name = request.args.get('p2_name', default='', type=str)
    char1 = request.args.get('char1')
    char2 = request.args.get('char2')
    p1_rank = request.args.get('p1_rank')
    p2_rank = request.args.get('p2_rank')
    order_by = request.args.get('order_by', default='date_added')
    game = request.args.get('game')
    page = request.args.get('page', 1, type=int)

    searchForm = SearchForm()

    pagination = queries.advanced_search(game_id=game,
                                         p1_rank=p1_rank,
                                         p2_rank=p2_rank,
                                         search_query=search,
                                         order_by=order_by,
                                         char1=char1,
                                         char2=char2,
                                         p1_name=p1_name,
                                         p2_name=p2_name
                                         ).paginate(page, per_page=9)
    replays = pagination.items

    return render_template('start.j2.html', pagination=pagination, replays=replays, form=searchForm, games=supported_games)


@app.route('/search', )
def search():
    search = request.args.get('search')
    order_by = request.args.get('order_by', default='date_added')
    game = request.args.get('game')
    page = request.args.get('page', 1, type=int)

    searchForm = SearchForm(request.form,
                            search=search,
                            game=game)

    if game == 'Any':
        game = '%'

    pagination = queries.basic_search(game, search, order_by).paginate(page, per_page=9)
    replays = pagination.items

    return render_template('start.j2.html', pagination=pagination, replays=replays, form=searchForm, games=supported_games)


@app.route('/search/player')
def search_player():
    searchForm = SearchForm()
    player = request.args.get('player')
    page = request.args.get('page', 1, type=int)
    pagination = queries.player_search(player).paginate(page, per_page=9)
    replays = pagination.items

    return render_template('start.j2.html', pagination=pagination, replays=replays, form=searchForm, games=supported_games)


@app.route('/robots.txt')
@app.route('/ads.txt')
def robots():
    return send_from_directory(app.static_folder, request.path[1:])


@app.route('/sitemap.xml')
def sitemap():
    tz = pytz.timezone("Pacific/Auckland")
    aware_dt = tz.localize(datetime.datetime.now())
    update_date = aware_dt.isoformat()
    return render_template('sitemap.j2.xml', update_date=update_date)


@app.route('/video/<challenge_id>')
def videopage(challenge_id):
    searchForm = SearchForm()

    replay = queries.single_replay(challenge_id)

    char_detect = queries.character_detect(challenge_id)

    characters = []
    for c in char_detect:
        characters.append(
            {
                'p1_char': c.p1_char,
                'p2_char': c.p2_char,
                'vid_time': c.vid_time,
                'seek_time': sum(int(x) * 60 ** i for i, x in enumerate(reversed(c.vid_time.split(":"))))
            }
        )

    seek = request.args.get('seek', default=0, type=float)

    logging.debug(
        f"Video page, replay: {replay}, characters: {characters}, seek: {seek}")
    return render_template('video.j2.html', replay=replay, characters=characters, seek=seek, form=searchForm, games=supported_games)


@app.route('/feed/atom')
def feed_atom():
    return Feed().render_atom()


@app.route('/feed/rss')
def feed_rss():
    return Feed().render_rss()

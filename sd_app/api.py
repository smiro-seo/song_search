from search import search_artist
from flask import Blueprint, request, jsonify
from flask_login import login_required
import sys
# from .func.wordpress import create_draft
from .constants import keys
sys.path.append('/..')

api = Blueprint('api', __name__)


@api.route('/search-artist/', methods=['GET'])
@login_required
def search_artist_api():
    artist_name = request.args.get('artist')
    print("Searching for artist: " + artist_name)

    results = search_artist(artist_name, keys).to_dict('records')

    return jsonify(results)

from search import search_artist
from flask import Flask, Blueprint, render_template, request, flash, jsonify, redirect, url_for, send_file
import json
import threading
from flask_login import login_required, current_user
from jinja2 import Environment, PackageLoader, select_autoescape
from .models import Search
from datetime import datetime as dt
from sqlalchemy.orm import scoped_session, sessionmaker, Query
from sqlalchemy import create_engine
import time
import pandas as pd
import sys
import os
from . import db, app
# from .func.wordpress import create_draft
from .constants import keys
sys.path.append('/..')

api = Blueprint('api', __name__)


@api.route('/search-artist/', methods=['GET'])
@login_required
def search_artist_api():
    artist_name = request.args.get('artist')
    print("Searching for artist: " + artist_name)

    results = search_artist(artist_name).to_dict('records')

    return jsonify(results)

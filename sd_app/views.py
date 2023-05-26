from search import search as song_search
from flask import Flask, Blueprint, render_template, request, flash, jsonify, redirect, url_for, send_file, render_template_string
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

flag_bkg = threading.Event()
stopper = threading.Event()

views = Blueprint('views', __name__)
input_data = pd.DataFrame(columns=['keyword', 'sp_keyword'])
input_path = os.path.join(os.path.dirname(__file__), '..', 'input.csv')


def save_input_data(input_data):
    input_data.to_csv(input_path, header=False)


def to_tuples(input_data):
    return list(input_data.itertuples(index=True, name=None))


def read_data():
    return pd.read_csv(input_path, names=['keyword', 'sp_keyword']).applymap(str)


def add_row(input_data, new_row):
    def check_kw(kw):
        flag = False
        if kw is None or kw == '' or len(kw) == 0:
            flag = True
        return flag

    # check n of columns
    if len(input_data.columns.values) != 2:
        return False, input_data, "An error ocurred. Try again."
    # check duplicates
    if input_data[(input_data.keyword == new_row['keyword']) & (input_data.sp_keyword == new_row['sp_keyword'])].shape[0] != 0:
        return False, input_data, "Keyword combination already exists."
    elif check_kw(new_row['keyword']) or check_kw(new_row['sp_keyword']):
        return False, input_data, "Keywords cannot be empty strings."
    else:
        input_data = pd.concat([input_data, pd.DataFrame(
            new_row, index=[1])], ignore_index=True)
        return True, input_data, 'Keyword added.'


def background_search(local_app, local_db, input_data, limit, offset, search_id, Search, wordpress,by_artist=False):

    with local_app.app_context():
        global flag_bkg, stopper

        flag_bkg.set()
        print("Background search running.")
        print(f"Limiting results to {limit}. Offset: {offset}")
        if not by_artist:
            input_data = input_data.rename(
            columns={'keyword': 'search_term', 'sp_keyword': 'keyword'})
        
        new_search = Search.query.get(search_id)
        
        try:
            csv_filename, html_filename = song_search(
                input_data,
                limit,
                offset,
                keys,
                stopper,
                wordpress,
                by_artist
            )
            if csv_filename == False or html_filename == False:
                flag_bkg.clear()
                return
            
            new_search.csv_path = csv_filename
            new_search.html_path = html_filename
            local_db.session.commit()
            print("Background search completed")
            local_db.session.close()
            flag_bkg.clear()
        except:
            new_search.csv_path = "Failed"
            new_search.html_path = "Failed"
            
            local_db.session.commit()
            print("Background search failed")
            local_db.session.close()
            flag_bkg.clear()



@views.route('/', methods=['GET', 'POST'])
@views.route('/search', methods=['GET', 'POST'])
@login_required
def search():

    global input_data, flag_bkg, app, stopper
    filename = ''

    if request.method == 'GET':

        input_data = read_data()

    if request.method == 'POST':
        data = dict(request.form)

        if data['option'] == 'input_row':
            data.pop('option', None)
            new_row = {x: y.lower() for x, y in data.items()}

            flag, input_data, msg = add_row(input_data, new_row)

            if flag:
                flash(msg, category='success')
            else:
                flash(msg, category='error')

            save_input_data(input_data)

        elif data['option'] == 'search':
            data.pop('option', None)

            try:
                limit_st = int(
                    data['limit-range-kw-txt']) if data.get('check-limit-kw', None) is not None else -1
                offset = int(
                    data['offset-range-txt']) if data.get('check-offset', None) is not None else 0
                if offset < 0 or limit_st < -1:
                    flash("Limits must be positive integer numbers. If you don't want to limit or offset the results, uncheck the checkbox", category='error')
                else:
                    if not flag_bkg.is_set():
                        stopper.clear()

                        input_data = read_data()
                        time_to_complete = 20*limit_st * \
                            len(set(input_data['keyword'].values))

                        keys['wp_user'] = data.get('wp-user', None)
                        keys['wp_password'] = data.get('wp-password', None)


                        new_search = Search(  # Create search without file path
                            user=current_user.username,
                            user_id=current_user.id,
                            keywords=input_data.to_json(),
                            csv_path="In progress",
                            html_path="In progress",
                            by_artist=0
                        )
                        db.session.add(new_search)
                        db.session.commit()
                        search_id = new_search.id
                        thread = threading.Thread(target=background_search, kwargs={
                            'local_app': app,
                            'local_db': db,
                            'input_data': input_data,
                            'limit': limit_st,
                            'offset': offset,
                            'search_id': search_id,
                            'Search': Search,
                            'wordpress':data.get('create-wordpress', False) 
                        })

                        thread.start()
                        flash(
                            f'Search running in background. Check the search history in about {int(time_to_complete/60)+1} minutes for the download link.', category='success')
                    else:
                        flash(
                            "There's another search running in the background. Try again in a few minutes. Check the search history for completion", category='error')

            except ValueError:
                flash("An error happened. Try again.", category='error')

    input_data_tuple = to_tuples(input_data)
    return render_template("search.html", input_data=input_data_tuple, download_link=filename, user=current_user)


@views.route('/search-by-artist', methods=['GET', 'POST'])
@login_required
def search_by_artist():
    global input_data, flag_bkg, app, stopper
    filename = ''

    if request.method == 'POST':
        data = json.loads(request.data)

        try:
            limit_st = int(
                data['limit-range-kw-txt']) if data.get('check-limit-kw', None) is not None else -1
            offset = int(
                data['offset-range-txt']) if data.get('check-offset', None) is not None else 0
            if offset < 0 or limit_st < -1:
                flash("Limits must be positive integer numbers. If you don't want to limit or offset the results, uncheck the checkbox", category='error')
            else:
                if not flag_bkg.is_set():
                    stopper.clear()

                    time_to_complete = 20*limit_st

                    new_search = Search(  # Create search without file path
                        user=current_user.username,
                        user_id=current_user.id,
                        keywords=data['artist-name'],
                        csv_path="In progress",
                        html_path="In progress",
                        by_artist=1
                    )
                    db.session.add(new_search)
                    db.session.commit()
                    search_id = new_search.id
                    thread = threading.Thread(target=background_search, kwargs={
                        'local_app': app,
                        'local_db': db,
                        'input_data': {"name":data['artist-name'], "id":data['artist-id']},
                        'limit': limit_st,
                        'offset': offset,
                        'search_id': search_id,
                        'Search': Search,
                        'wordpress':data.get('create-wordpress', False),
                        'by_artist':True
                    })

                    thread.start()
                    flash(
                        f'Search running in background. Check the search history in about {int(time_to_complete/60)+1} minutes for the download link.', category='success')
                else:
                    flash(
                        "There's another search running in the background. Try again in a few minutes. Check the search history for completion", category='error')

        except ValueError:
            flash("An error happened. Try again.", category='error')
        
        return jsonify({})

    return render_template("search_by_artist.html", user=current_user)


@views.route('/history', methods=['GET'])
@login_required
def history():

    return render_template("history.html",
                           user=current_user,
                           searches=Search.query.filter_by(user_id=current_user.id).order_by(
                               Search.date.desc()).all(),
                           json_load=json.loads,
                           set=set)


@views.route('/delete_row', methods=['POST'])
@login_required
def delete_row():
    global input_data
    data = json.loads(request.data)
    idx = data['idx']

    input_data = read_data()
    input_data.drop(index=idx, inplace=True)

    save_input_data(input_data)
    flash('Keyword deleted.', category='error')

    return jsonify({})


@views.route('/delete_search', methods=['POST'])
@login_required
def delete_search(flash_msg=True, idx=None):
    global stopper, flag_bkg

    if idx == None:
        idx = json.loads(request.data)['idx']
    search = Search.query.get(idx)

    if search.csv_path != "In progress":
        filepath = os.path.join(
            views.root_path, 'model_outputs', search.csv_path)
        if os.path.exists(filepath):
            print(f"File path to be deleted: {filepath}")
            os.remove(filepath)
    else:
        stopper.set()
        if flash_msg: flash("The search was stopped", category='error')
        flash_msg = False

    db.session.delete(search)
    db.session.commit()

    if flash_msg:
        flash('Search record deleted.', category='error')

    return jsonify({})


@views.route('/clear', methods=['POST'])
@login_required
def clear(flash_msg=True, what_to_clear=None):
    global input_data

    if what_to_clear is None:
        what_to_clear = json.loads(request.data)['what_to_clear']
    if what_to_clear == 'input':
        input_data = pd.DataFrame(columns=['keyword', 'sp_keyword'])

        save_input_data(input_data)
        if flash_msg:
            flash('Input data cleared.', category='error')

    elif what_to_clear == 'history':
        for search in Search.query.all():
            delete_search(flash_msg=False, idx=search.id)
        flash('Search history cleared.', category='error')

    return jsonify({})


@views.route('/repeat_search', methods=['POST'])
def repeat_search():
    global input_data
    search_input = json.loads(request.data)['keyword']

    clear(flash_msg=False, what_to_clear='input')
    input_data = pd.DataFrame(search_input)

    save_input_data(input_data)
    flash('Input data restored.', category='success')

    return jsonify({})


@views.route('/uploads/<path:filename>', methods=['GET', 'POST'])
@login_required
def download(filename):
    # Appending app path to upload folder path within app root folder
    path = os.path.join(views.root_path, 'model_outputs', filename)
    # Returning file from appended path
    return send_file(path, as_attachment=True)

@views.route('/html/<path:filename>', methods=['GET', 'POST'])
@login_required
def seeHTML(filename):
    # Appending app path to upload folder path within app root folder
    path = os.path.join(views.root_path, 'model_outputs', filename)

    with open(path, 'r') as f:
        html = f.read()
    # Returning file from appended path
    send_file(path, as_attachment=True)
    return render_template_string(html)

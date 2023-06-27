from search import Search_Keyword, Search_Artist
from flask import Flask, Blueprint, render_template, request, flash, jsonify, redirect, send_file, render_template_string
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
from .constants import keys, default_prompt, default_intro_prompt, default_intro_prompt_artist
sys.path.append('/..')

flag_bkg = threading.Event()
stopper = threading.Event()

views = Blueprint('views', __name__)
input_data = {'keywords':pd.DataFrame(columns=['keyword', 'sp_keyword']), 'prompt':default_prompt}
input_path = os.path.join(os.path.dirname(__file__), '..', 'input.csv')


def background_search(local_app, local_db, input_data, limit, offset,user,  by="keyword"):

    with local_app.app_context():
        global flag_bkg, stopper

        flag_bkg.set()
        print("Background search running.")
        print(f"Limiting results to {limit}. Offset: {offset}")
        print(user)
        
        if by=="keyword": search = Search_Keyword(input_data, limit, offset, keys, user)
        elif by=="artist": search = Search_Artist(input_data, limit, offset, keys, user)
        # Create db record
        search_record = search.create_record(Search, user)
        local_db.session.add(search_record)
        local_db.session.commit()

        # Run search
        status = search.run(flag_bkg, stopper)
        
        # Update status
        search_record.status = status

        # Close connections
        print("Background search " + status)
        local_db.session.commit()
        local_db.session.close()



@views.route('/', methods=['GET', 'POST'])
@views.route('/search/<by>', methods=['GET', 'POST'])
@login_required
def search(by="keyword"):

    global input_data, flag_bkg, app, stopper

    if by=="artist":
        intro_prompt = current_user.default_intro_prompt_artist
        prompt = current_user.default_prompt_artist
    elif by=="keyword":
        intro_prompt = current_user.default_intro_prompt
        prompt = current_user.default_prompt
        
    improver_prompt = current_user.default_improver_prompt
    improved = {'intro':True,'song':True}
    search_id = request.args.get('search_id', None)
    model='gpt-3.5-turbo'

    artist=""
    keywords = {'keyword': '', 'sp_keywords':[]}
    
    if request.method == 'GET':

        if search_id is not None:
            flash('Input data restored.', category='success')
            search = Search.query.get(search_id)

            if by=="keyword":
                keywords = {'sp_keywords':search.sp_keywords, 'keyword': search.keyword}

            elif by=="artist":
                artist = search.keywords

            prompt = search.prompt
            intro_prompt = search.intro_prompt
            improver_prompt = search.improver_prompt
            improved = {'intro':search.improved_intro,'song':search.improved_song}
            model=search.model

    elif request.method == 'POST':
        data = json.loads(request.data)
        print(data)

        if "`" in data.get('prompt', "")+ data.get("intro-prompt", "")+ data.get("improver-prompt", ""):
            flash("Backticks (`) are not allowed in the prompts. You can use both simple or double quotes.", category='error' )


        else:
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
                        if data.get("improve_song", False): time_to_complete*=2

                        thread = threading.Thread(target=background_search, kwargs={
                            'local_app': app,
                            'local_db': db,
                            'input_data': data,
                            'limit': limit_st,
                            'offset': offset,
                            'user':current_user.dict_data(),
                            'by':by
                        })

                        thread.start()


                        #   Set default prompts if selected
                        if data.get('default-prompt', False):
                            if by=="artist": current_user.default_prompt_artist = data['prompt']
                            elif by=="keyword": current_user.default_prompt = data['prompt']
                            prompt=data['prompt']

                        if data.get('default-intro-prompt', False):
                            if by=="artist": current_user.default_intro_prompt_artist = data['intro-prompt']
                            elif by=="keyword": current_user.default_intro_prompt = data['intro-prompt']
                            intro_prompt=data['intro-prompt']

                        if data.get('default-improver-prompt', False):
                            current_user.default_improver_prompt = data['improver-prompt']
                            improver_prompt=data['improver-prompt']
                        
                        db.session.commit()
                        flash(
                            f'Search running in background. Check the search history in about {int(time_to_complete/60)+1} minutes for the download link.', category='success')
                    else:
                        flash(
                            "There's another search running in the background. Try again in a few minutes. Check the search history for completion", category='error')

            except ValueError as e:
                flash("An error happened. Try again.", category='error')
                print("ERROR")
                print(e)


    return render_template(f"search_by_{by}.html", 
                           keywords=keywords,
                           artist=artist,
                           user=current_user.dict_data(),
                           prompt=prompt,
                           intro_prompt=intro_prompt,
                           improver_prompt=improver_prompt,
                           existing = search_id is not None,
                           improved=improved,
                           model=model,
                           by=by)


@views.route('/history', methods=['GET'])
@login_required
def history():

    return render_template("history.html",
                           user=current_user,
                           searches=Search.query.order_by(Search.date.desc()).all(),
                           json_load=json.loads,
                           set=set)


@views.route('/delete_search', methods=['POST'])
@login_required
def delete_search(flash_msg=True, idx=None):
    global stopper, flag_bkg

    if idx == None:
        idx = json.loads(request.data)['idx']
    search = Search.query.get(idx)

    if search.status == "In progress":
        stopper.set()
        flag_bkg.clear()
        if flash_msg: flash("The search was stopped", category='error')
        search.status = "Stopped"
        flash_msg = False
    else:
        db.session.delete(search)
    
    db.session.commit()

    if flash_msg:
        flash('Search record deleted.', category='error')

    return jsonify({})


@views.route('/clear-history', methods=['POST'])
@login_required
def clear_history(flash_msg=True):
    global input_data

    for search in Search.query.all():
        delete_search(flash_msg=False, idx=search.id)
    flash('Search history cleared.', category='error')

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

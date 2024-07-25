from search import Search_Keyword, Search_Artist, Search_Spotify_Keyword, Search_Spotify_Artist
from flask import Flask, Blueprint, render_template, request, flash, jsonify, redirect, send_file, render_template_string, url_for
import json
import threading
from flask_login import login_required, current_user
from jinja2 import Environment, PackageLoader, select_autoescape
from .models import Search, Def_Search, SpotifyDraft
from datetime import datetime as dt
import time
import pandas as pd
import sys
import os
from . import db, app
from .constants import keys, default_prompt, default_intro_prompt, default_intro_prompt_artist, aspect_ratios
sys.path.append('/..')
import spotipy 
from spotipy.oauth2 import SpotifyClientCredentials


def fix_str_html(string):
    new_string = string.replace('[NEWLINE]', '<br/>')
    print(new_string)
    return new_string
test = 'Based on the following article summary, provide a suitable prompt for a text-to-image generative model. Focus on the concept of [keyword]. Below are some examples:\nExample 1:\nA dreamy, vibrant illustration about [keyword]; aesthetically pleasing anime style, trending on popular art platforms, minutely detailed, with precise, sharp lines, a composition that qualifies as an award-winning illustration, presented in 4K resolution, inspired by master artists like Eugene de Blaas and Ross Tran, employing a vibrant color palette, intricately detailed.\nExample 2:\nAn illustration exuding van gogh distinctive style; an ultra-detailed and hyper-realistic portrayal of [keyword], designed with Lisa Frank aesthetics, featuring popular art elements such as butterflies and florals, sharp focus, akin to a high-quality studio photograph, with meticulous detailing.'
fix_str_html(test)


flag_bkg = threading.Event()
stopper = threading.Event()

views = Blueprint('views', __name__)
input_data = {'keywords':pd.DataFrame(columns=['keyword', 'sp_keyword']), 'prompt':default_prompt}
input_path = os.path.join(os.path.dirname(__file__), '..', 'input.csv')


def background_search(local_app, local_db, input_data, limit, offset,user, by):

    with local_app.app_context():
        global flag_bkg, stopper

        flag_bkg.set()
        print("Background search running.")
        print(f"Limiting results to {limit}. Offset: {offset}")

        print("in background search", by)

        print("OKAY")
        print("-----------------------------")
        print(input_data)
        print("-----------------------------")
        

        if by=="keyword": search = Search_Keyword(input_data, limit, offset, keys, user, by)
        elif by=="artist": search = Search_Artist(input_data, limit, offset, keys, user, by)
        
        # Create db record
        search_record = search.create_record(Search, user)
        local_db.session.add(search_record)
        local_db.session.commit()

        # # Run search
        status = search.run(flag_bkg, stopper)
        local_db.session.commit()
        
        # Update status
        search_record.status = status

        # Close connections
        print("Background search " + status)
        local_db.session.commit()
        local_db.session.close()


def background_spotify_search(local_app, local_db, input_data, limit, offset, user, by="keyword", keyword=None, sp_keywords=None):
    # Your code here

    with local_app.app_context():
        global flag_bkg, stopper

        flag_bkg.set()
        print("Background search running.")
        print(f"Limiting results to {limit}. Offset: {offset}")
        
        if by=="keyword": search = Search_Spotify_Keyword(input_data, limit, offset, keys, user)
        elif by=="artist": search = Search_Spotify_Artist(input_data, limit, offset, keys, user)

        search_results = search.run(flag_bkg, stopper)

        print("search_results", search_results)
        
        for index, row in search_results.iterrows():
            print('row',row)
            try:
                artist = row['artist']
                track_name = row['track_name']
                release_year = row['release_year']
                album = row['album']
                popularity = row['popularity']
                duration_ms = row['duration_ms']
                track_id = row['track_id']
                spotify_url = row['spotify_url']
                track_name_clean = row['track_name_clean']

                keyword = keyword

                search_record = search.create_spotify_draft(SpotifyDraft, keyword, str(sp_keywords), user, by , artist, track_name, release_year, album, popularity, duration_ms, track_id, spotify_url, track_name_clean)
                print("search_record", search_record)
                local_db.session.add(search_record)
                local_db.session.commit()
                local_db.session.close()
            except Exception as e:
                print("Error while running search keyword")
                print(e)
                return "Failed"



        # for result in search_results:
        #     print('result',result)
        #     search_record = search.create_spotify_draft(SpotifyDraft, user, artist, track_name , release_year, alubum , popularity, duration_ms, track_id, spotify_url, track_name_clean)
        #     local_db.session.add(search_record)
        #     local_db.session.commit()
        #     local_db.session.close()

        

@views.route('/', methods=['GET', 'POST'])
@views.route('/search/<by>', methods=['GET', 'POST'])
@login_required
def search(by="keyword"):

    global input_data, flag_bkg, app, stopper
    search_id = request.args.get('search_id', None)
    search = Def_Search(current_user, by)

    if request.method == 'GET' and search_id is not None:

        search_found = Search.query.get(search_id)
        if search_found: 
            flash('Input data restored.', category='success')
            search = search_found
        else:
            flash("There was an error recovering search data", category='error')
            
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

                        if data.get('default-img-prompt', False):
                            current_user.default_img_prompt = data['img-prompt']
                            improver_prompt=data['img-prompt']
                        

                        img_config = data.get('img-config', json.loads(current_user.default_img_config))
                        def_img_config = {}
                        for config in data.get('default-img-config', []):
                            def_img_config[config]= img_config.get(config, "")
                        current_user.default_img_config = json.dumps(json.loads(current_user.default_img_config) | def_img_config)


                        db.session.commit()
                        flash(
                            f'Search running in background. Check the search history in about {int(time_to_complete/60)+1} minutes for the download link.', category='success')
                    else:
                        print("another thread is already running")
                        flash(
                            "There's another search running in the background. Try again in a few minutes. Check the search history for completion", category='error')

            except ValueError as e:
                flash("An error happened. Try again.", category='error')
                print("ERROR")
                print(e)

    return render_template(f"search_by_{by}.html", 
                           search=search,
                           user=current_user.dict_data(),
                           existing = search_id is not None,
                           aspect_ratios=aspect_ratios
                           )

@views.route('/searchSpotify/<by>',methods=['GET', 'POST'])
def searchSpotify(by="keyword"):
    global input_data, flag_bkg, app, stopper
    search_id = request.args.get('search_id', None)
    search = Def_Search(current_user, by)

    if request.method == 'GET' and search_id is not None:

        search_found = Search.query.get(search_id)
        if search_found: 
            flash('Input data restored.', category='success')
            search = search_found
        else:
            flash("There was an error recovering search data", category='error')
    elif request.method == 'POST':
        data = json.loads(request.data)
        print(data)
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

                    print("spotifysearchby ", by)

                    thread = threading.Thread(target=background_spotify_search, kwargs={
                        'local_app': app,
                        'local_db': db,
                        'input_data': data,
                        'limit': limit_st,
                        'offset': offset,
                        'user':current_user.dict_data(),
                        'by':by,
                        'keyword': data.get('keyword', ''),
                        'sp_keywords': data.get('sp_keywords', '')
                    })

                    thread.start()

                    db.session.commit()
                    flash(
                        f'Search running in background. Check the search history in about {int(time_to_complete/60)+1} minutes for the download link.', category='success')
                else:
                    print("another thread is already running")
                    flash(
                        "There's another search running in the background. Try again in a few minutes. Check the search history for completion", category='error')

        except ValueError as e:
            flash("An error happened. Try again.", category='error')
            print("ERROR")
            print(e)


    return render_template(f"search_by_{by}.html", 
                        search=search,
                        user=current_user.dict_data(),
                        existing = search_id is not None,
                        aspect_ratios=aspect_ratios
                        )

@views.route('/proceed/<by>',methods=['GET', 'POST'])
def proceedAI(by):
        global input_data, flag_bkg, app, stopper
        search_id = request.args.get('search_id', None)
        search = Def_Search(current_user, by)
        print("proceedingby", by)

        songs = SpotifyDraft.query.filter(SpotifyDraft.searchedby.contains(by)).order_by(SpotifyDraft.popularity.desc()).all()
        first_song = songs[0]

        if request.method == 'GET' and search_id is not None:

            search_found = Search.query.get(search_id)
            if search_found: 
                flash('Input data restored.', category='success')
                search = search_found
            else:
                flash("There was an error recovering search data", category='error')
                
        elif request.method == 'POST':
            data = json.loads(request.data)
            keyword = data.get("keyword", "")
            print(data)
            print(keyword)

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

                            if data.get('default-img-prompt', False):
                                current_user.default_img_prompt = data['img-prompt']
                                improver_prompt=data['img-prompt']
                            

                            img_config = data.get('img-config', json.loads(current_user.default_img_config))
                            def_img_config = {}
                            for config in data.get('default-img-config', []):
                                def_img_config[config]= img_config.get(config, "")
                            current_user.default_img_config = json.dumps(json.loads(current_user.default_img_config) | def_img_config)


                            db.session.commit()
                            flash(
                                f'Search running in background. Check the search history in about {int(time_to_complete/60)+1} minutes for the download link.', category='success')
                            # if not flag_bkg.is_set():

                            # else:
                            #     print("another thread is already running")
                            #     flash(
                            #         "There's another search running in the background. Try again in a few minutes. Check the search history for completion", category='error')
                        else:
                            flash("There's another search running in the background. Try again in a few minutes")
                except ValueError as e:
                    flash("An error happened. Try again.", category='error')
                    print("ERROR")
                    print(e)

        return render_template(f"proceed.html", 
                            user=current_user.dict_data(),
                            search=search,
                            first_song = first_song,
                            existing = False,
                            aspect_ratios=aspect_ratios
                            )

@views.route('/history', methods=['GET'])
@login_required
def history():

    return render_template("history.html",
                           user=current_user,
                           searches=Search.query.order_by(Search.date.desc()).all(),
                           json_load=json.loads,
                           set=set)

@views.route('/spotifyDrafts/<by>', methods=['GET'])
@login_required
def spotifyDrafts(by):
    if by == 'artist':
        print('searching by artist')
        return render_template("spotify_drafts.html",
                            by=by,
                            user=current_user,
                            drafts=SpotifyDraft.query.filter(SpotifyDraft.searchedby.contains(by)).order_by(SpotifyDraft.popularity.desc()).all(),
                            json_load=json.loads,
                            set=set)
    else :
        print("searching by keyword")
        return render_template("spotify_drafts.html",
                            by=by,
                            user=current_user,
                            drafts=SpotifyDraft.query.filter(SpotifyDraft.searchedby.contains(by)).order_by(SpotifyDraft.popularity.desc()).all(),
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

@views.route('/deleteSpotifyDraft', methods=['POST'])
@login_required
def delete_spotifydraft(flash_msg=True, idx=None):
    global stopper, flag_bkg

    if idx == None:
        idx = json.loads(request.data)['idx']

    draft = SpotifyDraft.query.get(idx)

    db.session.delete(draft)
    
    db.session.commit()

    if flash_msg:
        flash('Draft record deleted.', category='error')

    return jsonify({})

@views.route('/deleteSelected/<by>', methods=['POST'])
@login_required
def delete_selected(by):
    selected_drafts = request.form.getlist('selected_drafts')
    print("deleting selected")
    for id in selected_drafts:
        db.session.query(SpotifyDraft).filter(SpotifyDraft.id == id).delete()
    db.session.commit()
    return redirect(url_for('views.spotifyDrafts', by=by))

@views.route('/clear-history', methods=['POST'])
@login_required
def clear_history(flash_msg=True):
    global input_data

    for search in Search.query.all():
        delete_search(flash_msg=False, idx=search.id)
    flash('Search history cleared.', category='error')

    return jsonify({})


@views.route('/clear-spotifyDraft', methods=['POST'])
@login_required
def clear_spotify_draft(flash_msg=True):
    global input_data

    for draft in SpotifyDraft.query.all():
        delete_spotifydraft(flash_msg=False, idx=draft.id)
    flash('Spotify draft cleared.', category='error')

    return jsonify({})


@views.route('/uploads/<path:filename>', methods=['GET', 'POST'])
@login_required
def download(filename):
    # Appending app path to upload folder path within app root folder
    path = os.path.join(views.root_path, '..', '..', '..', 'var', 'song_search', 'model_outputs', filename)
    # Returning file from appended path
    return send_file(path, as_attachment=True)

@views.route('/html/<path:filename>', methods=['GET', 'POST'])
@login_required
def seeHTML(filename):
    # Appending app path to upload folder path within app root folder
    path = os.path.join(views.root_path, '..', '..', '..', 'var', 'song_search', 'model_outputs', filename)

    with open(path, 'r') as f:
        html = f.read()
    # Returning file from appended path
    send_file(path, as_attachment=True)
    return render_template_string(html)


@views.route("/single_search", methods=["GET", "POST"])
@login_required
def singleSearch():
    sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(client_id=keys['sp_user'], client_secret=keys['sp_password']), requests_timeout=60)

    last = SpotifyDraft.query.filter(SpotifyDraft.user == current_user.username).order_by(SpotifyDraft.date.desc()).first()

    if last:
        print("last",last)
        last_keyword = last.keyword
    else:
        print("setting it to the next")
        last_keyword = ""
    
    print("last_keyword", last_keyword)

    if request.method == "GET":
        return render_template("single_search.html",
                               user=current_user,
                               aspect_ratios=aspect_ratios,
                               last_keyword = last_keyword,
                               spotifyResponse={},
                               )
    if request.method == "POST":
        track_id = request.form.get('trackId')
        artist_name = request.form.get('artistName')
        track_name = request.form.get('trackName')
        searchByTrackId = request.form.get('searchByTrackId')

        print("track_id", track_id, "artist_name", artist_name, "track_name", track_name, searchByTrackId)

        if track_id:
            track = sp.track(track_id)
            if track:
                spotifyResponse =  {
                    'artist': ', '.join([artist['name'] for artist in track['artists']]),
                    'track': track['name'],
                    'album': track['album']['name'],
                    'popularity': track['popularity'],
                    'release_year': track['album']['release_date'][:4],
                    'release_date': track['album']['release_date'],
                    'preview_url': track['preview_url'],
                    'external_url': track['external_urls']['spotify'],
                    'track_id': track['id'],
                    'duration_ms': track['duration_ms']
                }

                return render_template("single_search.html",
                                    user=current_user,
                                    aspect_ratios=aspect_ratios,
                                    last_keyword = last_keyword,
                                    spotifyResponse=spotifyResponse
                                    )
            else:
                return render_template("single_search.html",
                                user=current_user,
                                aspect_ratios=aspect_ratios,
                                last_keyword = last_keyword,
                                spotifyResponse={}
                                )
        else:
            query = f'artist:{artist_name} track:{track_name}'
            results = sp.search(q=query, type='track', limit=1)
            if results['tracks']['items']:
                track = results['tracks']['items'][0]

                spotifyResponse =  {
                    'artist': ', '.join([artist['name'] for artist in track['artists']]),
                    'track': track['name'],
                    'album': track['album']['name'],
                    'popularity': track['popularity'],
                    'release_year': track['album']['release_date'][:4],
                    'release_date': track['album']['release_date'],
                    'preview_url': track['preview_url'],
                    'external_url': track['external_urls']['spotify'],
                    'track_id': track['id'],
                    'duration_ms': track['duration_ms']
                }

                return render_template("single_search.html",
                                    user=current_user,
                                    aspect_ratios=aspect_ratios,
                                    last_keyword = last_keyword,
                                    spotifyResponse=spotifyResponse
                                    )
            else:
                flash('No results found', category='error')
                return render_template("single_search.html",
                                    user=current_user,
                                    aspect_ratios=aspect_ratios,
                                    spotifyResponse={}
                                    )


@views.route("/add_to_draft",methods=["POST"])
@login_required
def add_to_draft():
    if request.method == "POST":
        data = request.form.to_dict()
        print('here is the data to add',data, request.form)
        try:    
            submit_type = request.form.get('submitType') 

            notset = "notset"

            if submit_type == "artist":
                search_record = SpotifyDraft(
                    keyword = data.get('keyword', notset),
                    sp_keywords = data.get('sp_keyword', ''),
                    searchedby = "artist",
                    user = current_user.username,
                    artist = data.get('artist', ''),
                    track_name = data.get('track_name', ''),
                    release_year = data.get('release_year', ''),
                    #album = data.get('album', ''),
                    popularity = data.get('popularity', ''),
                    duration_ms = data.get('duration_ms', ''),
                    track_id = data.get('track_id', ''),
                    spotify_url = data.get('external_url', ''),
                    track_name_clean = data.get('track_name', '')
                )
                db.session.add(search_record)
                db.session.commit()
                flash('Draft added successfully', category='success') 
                return redirect(url_for('views.singleSearch'))
            else:
                search_record = SpotifyDraft(
                    keyword = data.get('keyword', notset),
                    sp_keywords = data.get('sp_keyword', '[' + data.get('track_name', '')) + ']',
                    searchedby = "keyword",
                    user = current_user.username,
                    artist = data.get('artist', ''),
                    track_name = data.get('track_name', ''),
                    release_year = data.get('release_year', ''),
                    #album = data.get('album', ''),
                    popularity = data.get('popularity', ''),
                    duration_ms = data.get('duration_ms', ''),
                    track_id = data.get('track_id', ''),
                    spotify_url = data.get('external_url', ''),
                    track_name_clean = data.get('track_name', '')
                )
                db.session.add(search_record)
                db.session.commit()
                flash('Draft added successfully', category='success')
                return redirect(url_for('views.singleSearch'))
        except Exception as e:
            print("Error while adding to draft")
            print(e)
            flash('Error while adding to draft', category='error')
            return redirect(url_for('views.singleSearch'))
    else:
        flash('Error while adding to draft', category='error')
        return redirect(url_for('views.singleSearch'))

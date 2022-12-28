from flask import Blueprint, render_template, request, flash, jsonify, redirect, url_for, send_file
import json
from flask_login import login_required, current_user
from jinja2 import Environment, PackageLoader, select_autoescape
from .models import Search
from datetime import datetime as dt
import time
import pandas as pd
import sys
import os
from . import db
from .constants import keys
from flask import current_app as app
sys.path.append('/..')
from search import search as song_search

views = Blueprint('views', __name__)
input_data = pd.DataFrame(columns=['keyword', 'sp_keyword'])
input_path = os.path.join(views.root_path, '..', 'input.csv')

def save_input_data(input_data):
    input_data.to_csv(input_path, header=False)
    
def to_tuples(input_data):
    return list(input_data.itertuples(index=True, name=None))

def read_data():
    return pd.read_csv(input_path,names=['keyword', 'sp_keyword']).applymap(str)

def add_row(input_data, new_row):
    #check n of columns
    if len(input_data.columns.values) != 2:
        return False, input_data, "An error ocurred. Try again."
    #check duplicates
    if input_data[(input_data.keyword == new_row['keyword']) & (input_data.sp_keyword == new_row['sp_keyword'])].shape[0] != 0:
        return False, input_data, "Keyword combination already exists."
    else:
        input_data = pd.concat([input_data, pd.DataFrame(new_row, index=[1])], ignore_index=True)
        return True, input_data, 'Keyword added.'

'''     SCHEDULED NOT WORKING ON PYTHONANYWHERE
def queue_search(input_data, limit, offset, time_to_complete):
    queue_path = os.path.join(views.root_path, '..', 'queue.txt')

    input_data_dict['input_data'] = input_data.to_dict()
    input_data_dict['limit'] = limit
    input_data_dict['offset'] = offset

    input_data_json = json.dumps(input_data_dict)

    try:
        with open(queue_path, 'a') as f:
            f.write(f'{input_data_json}\n')
        
        msg = f'Search running in background. Check the search history in about {int(time_to_complete/60)+1} minutes for the download link.'
        print('Search added to queue')
    except Exception as e:
        msg = 'There was an error while writing into the queue. Try again in a few minutes'
        print('There was an error while writing into the queue')
        print(e)
    
    return msg
'''

@views.route('/', methods=['GET', 'POST'])  
@views.route('/search', methods=['GET', 'POST']) 
@login_required 
def search():

    global input_data
    filename=''

    if request.method == 'GET':

        input_data = read_data()

    if request.method == 'POST':
        
        data = dict(request.form)
        
        if data['option'] == 'input_row':
            data.pop('option', None)
            new_row = {x:y.lower() for x,y in data.items()}

            flag, input_data, msg = add_row(input_data,new_row)
            
            if flag:
                flash(msg, category='success')
            else:
                flash(msg, category='error')
            
            save_input_data(input_data)

        elif data['option'] == 'search':
            data.pop('option', None)

            try:
                limit_st = int(data['limit-range-kw-txt']) if data.get('check-limit-kw', None) is not None else -1
                limit_tot=-1
                offset = int(data['offset-range-txt']) if data.get('check-offset', None) is not None else 0
                if offset < 0 or limit_st < -1:
                    flash("Limits must be positive integer numbers. If you don't want to limit or offset the results, uncheck the checkbox", category='error')
                else:
                    input_data = read_data()
                    #time_to_complete = 20*limit_st*len(set(input_data['keyword'].values))
                    #if time_to_complete <= 330:     #If it takes less than 5 minutes (timeout limit in PA)

                    filename = song_search(
                        input_data.rename(columns={'keyword': 'search_term', 'sp_keyword':'keyword'}),
                        limit_st,
                        offset,
                        keys
                    )

                    new_search = Search(
                        user = current_user.username,
                        keywords = input_data.to_json(),
                        csv_path = filename
                    )
                    db.session.add(new_search)
                    db.session.commit()
                    flash('Search completed.', category='download')
                    '''
                    else:           #If the task will take longer, put search on queue
                        msg = queue_search(input_data.rename(columns={'keyword': 'search_term', 'sp_keyword':'keyword'}), limit_st, offset, time_to_complete)
                        flash(msg, category='success')
                    '''
            except ValueError:
                flash("An error happened. Try again.", category='error')

    input_data_tuple = to_tuples(input_data)    
    return render_template("search.html", input_data = input_data_tuple, download_link=filename, user=current_user)

@views.route('/history', methods=['GET']) 
@login_required 
def history():
  
    return render_template("history.html",
    user=current_user,
    searches=Search.query.order_by(Search.date.desc()).all(),
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
def delete_search():
    
    data = json.loads(request.data)
    idx = data['idx']
    search = Search.query.get(idx)

    filepath = os.path.join(views.root_path, 'model_outputs', search.csv_path)
    print(f"File path to be deleted: {filepath}")
    os.remove(filepath)

    db.session.delete(search)
    db.session.commit()

    flash('Search record deleted.', category='error')

    return jsonify({})

@views.route('/clear_input', methods=['POST'])  
@login_required
def clear_input(flash_msg=True):
    global input_data
    
    input_data = pd.DataFrame(columns=['keyword', 'sp_keyword'])

    save_input_data(input_data)
    if flash_msg: flash('Input data cleared.', category='error')

    return jsonify({})

@views.route('/repeat_search', methods=['POST'])
def repeat_search():
    global input_data
    search_input = json.loads(request.data)['keyword']

    clear_input(flash_msg=False)
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
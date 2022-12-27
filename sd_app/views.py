from flask import Blueprint, render_template, request, flash, jsonify, redirect, url_for, send_file
import json 
from flask_login import login_required, current_user
from jinja2 import Environment, PackageLoader, select_autoescape
from .models import Search
from datetime import datetime as dt
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
    return pd.read_csv(input_path,names=['keyword', 'sp_keyword'])

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
                #limit_tot = int(data['limit-range-txt']) if data.get('check-limit', None) is not None else -1
                if limit_tot < -1 or limit_st < -1:
                    flash("Limits must be positive integer numbers. If you don't want to limit the results, uncheck the checkbox", category='error')
                else:
                    input_data = read_data()
                    filename = song_search(
                        input_data.rename(columns={'keyword': 'search_term', 'sp_keyword':'keyword'}),
                        limit_st,
                        limit_tot,
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
            
            except ValueError:
                flash("Limits must be integer numbers. If you don't want to limit the results, uncheck the checkbox", category='error')

    input_data_tuple = to_tuples(input_data)    
    return render_template("search.html", input_data = input_data_tuple, download_link=filename, user=current_user)

@views.route('/history', methods=['GET']) 
@login_required 
def history():
  
    return render_template("history.html", user=current_user, searches=Search.query.order_by(Search.date.desc()).all())

@views.route('/change_password', methods=['GET', 'POST']) 
@login_required 
def change_password():


    return render_template("change_password.html", user=current_user)


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
    db.session.delete(search)
    db.session.commit()

    flash('Search record deleted.', category='error')

    return jsonify({})

@views.route('/clear_input', methods=['POST'])  
@login_required
def clear_input():
    global input_data
    
    input_data = pd.DataFrame(columns=['keyword', 'sp_keyword'])

    save_input_data(input_data)
    flash('Input data cleared.', category='error')

    return jsonify({})

@views.route('/repeat_search', methods=['POST'])
def repeat_search():
    global input_data
    search_input = request.data
    
    input_data = pd.DataFrame(search_input)

    save_input_data(input_data)
    flash('Input data restored.', category='error')

    return jsonify({})

@views.route('/uploads/<path:filename>', methods=['GET', 'POST'])
@login_required
def download(filename):
    # Appending app path to upload folder path within app root folder
    path = os.path.join(views.root_path, 'model_outputs', filename)
    # Returning file from appended path
    return send_file(path, as_attachment=True)
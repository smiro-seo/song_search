import pandas as pd
from .models import Search
from .views import views
import sys
import os
from . import db
from .constants import keys
sys.path.append('/..')
from search import search as song_search

def perform_search(input_data, limit_st, offset, keys):
    
    filename = song_search(
        input_data.rename(columns={'keyword': 'search_term', 'sp_keyword':'keyword'}),
        limit_st,
        offset,
        keys
    )

    return Search(
        user = current_user.username,
        keywords = input_data.to_json(),
        csv_path = filename
    )

def read_queue():

    queue_path = os.path.join(views.root_path, '..', 'queue.txt')
    with open(queue_path, 'r+') as f:
        queue = f.readlines()
        f.truncate(0)

    return queue

def main_proc():
    global keys
    queue = read_queue()

    for search in queue:
        input_data = search['input_data']
        limit = search['limit']
        offset = search['offset']

        search_record = perform_search(input_data, limit_st, offset, keys)
        db.session.add(search_record)

    db.session.commit()

main_proc()
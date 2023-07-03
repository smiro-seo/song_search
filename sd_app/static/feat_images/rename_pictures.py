import os
import sqlite3
import pandas as pd
import json
import numpy as np

def clean_name(name):
    new_name = name.replace(' ', '_').replace('-', '_').replace('(', '').replace(')', '').replace('.', '').replace(',', '')
    return new_name


conn = sqlite3.connect('./../../../instance/database.db')
cur = conn.cursor()

searches = pd.read_sql_query("SELECT id, keywords, by FROM search", conn)

print("Files: " + str(os.listdir()))

for pic_name in os.listdir():
    
    if 'feat_img' in pic_name:
        search_id = np.int64(pic_name.split('_')[-1].split('.')[0])

        if search_id in list(searches['id'].values):

            search = searches[searches['id']==search_id].iloc[0]
            print(search)

            if search['by']=='artist':
                kw = search['keywords']
            else:
                kw = json.loads(search['keywords'])['keyword']
            
            kw = clean_name(kw)

            new_name = f'{kw}_songs_{search_id}.png'
            os.rename(pic_name, new_name)

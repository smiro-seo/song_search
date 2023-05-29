import requests
import json
from base64 import b64encode
from datetime import datetime
from requests.auth import HTTPBasicAuth


def create_wp_draft(title, html, slug, keys):
    url = "https://songpier.com/wp-json/wp/v2/posts"
    user = keys['wp_user']
    password = keys['wp_password']
    credentials = str(user) + ':' + str(password)
    token = b64encode(credentials.encode('utf-8')).decode('ascii')
    header_auth = {'Authorization': 'Basic ' + token}
    headers = {
    "Accept": "application/json",
    "Content-Type": "application/json"
    }
    auth=HTTPBasicAuth(user, password)
    post = {
        'title': title,
        'status': 'draft',
        'slug':slug,
        'content': html,
        #'categories': 1,  # category ID
        'date': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    print("Creating wordpress draft...")
    
    response = requests.post(url, json=post, headers=header_auth)
    

    if response.status_code==401 or response.status_code=="401":
        response = requests.post(url, json=post, auth=auth, headers=headers)

    return

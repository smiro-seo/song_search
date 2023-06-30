import requests
import json
from base64 import b64encode
from datetime import datetime
from requests.auth import HTTPBasicAuth

base_url = "https://songpier.com/wp-json/wp/v2"

def create_wp_draft(title, html, slug, keys, image_id=None):

    url = f"{base_url}/posts"
    auth = get_wp_auth(keys)
    headers = {'Authorization': auth,"Content-Type": "application/json"}

    '''headers = {
    "Accept": "application/json",
    "Content-Type": "application/json"
    }'''

    post = {
        'title': title,
        'status': 'draft',
        'slug':slug,
        'content': html,
        #'categories': 1,  # category ID
        'date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'featured_media':image_id
    }

    print("Creating wordpress draft...")
    
    send_wp_request(url, post, headers)
    

    return

def add_wp_image(img_bin, img_name, keys):

    url = f"{base_url}/media"
    auth = get_wp_auth(keys)
    headers = {'Authorization': auth, "Content-Type": "image/png", "Content-Disposition": f'attachment; filename:"{img_name}.png"'}

    media = {
        'title': img_name,
        'status': 'draft',
        'date': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    print("Creating wordpress image...")
    
    res = send_wp_request(url, media, headers).json()

    print(res)

    return res.get('id', None)
    

def get_wp_auth(keys):
    user = keys['wp_user']
    password = keys['wp_password']
    credentials = str(user) + ':' + str(password)
    token = b64encode(credentials.encode('utf-8')).decode('ascii')
    return 'Basic ' + token

def send_wp_request(url, post, headers):

    response = requests.post(url, json=post, headers=headers)
    return response
    '''
    if response.status_code==401 or response.status_code=="401":
        response = requests.post(url, json=post, auth=auth, headers=headers)
    '''
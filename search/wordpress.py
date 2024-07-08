import requests
import json
from base64 import b64encode
from datetime import datetime
from .const import default_img_format
from requests.auth import HTTPBasicAuth

BY_ARTIST_CATEGORY=24
BY_KEYWORD_CATEGORY=25
PARENT_CATEGORY=3

base_url = "https://songpier.com/wp-json/wp/v2"

def create_wp_draft(title, html, slug, keys, image_id=None, by="artist"):

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
        'categories': json.dumps([PARENT_CATEGORY, BY_ARTIST_CATEGORY if by=="artist" else BY_KEYWORD_CATEGORY]),  # category ID
        'date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'featured_media':image_id
    }

    print("Creating wordpress draft...")
    
    send_wp_request(url, {"json":post}, headers)
    

    return

def add_wp_image(img_bin, img_name, keys):

    url = f"{base_url}/media"
    auth = get_wp_auth(keys)
    headers = {'Authorization': auth, "Content-Type": f"image/{default_img_format}", "Content-Disposition": f'attachment; filename="{img_name}"'}

    print("Creating wordpress image...")
    res = send_wp_request(url, {'data':img_bin},  headers).json()

    print(res)

    return res.get('id', None)
    

def get_wp_auth(keys):
    user = keys['wp_user']
    password = keys['wp_password']
    credentials = str(user) + ':' + str(password)
    token = b64encode(credentials.encode('utf-8')).decode('ascii')
    return 'Basic ' + token

def send_wp_request(url, post, headers):

    response = requests.post(url, headers=headers, **post)
    print("WP response:")
    print(response.json())
    return response
    '''
    if response.status_code==401 or response.status_code=="401":
        response = requests.post(url, json=post, auth=auth, headers=headers)
    '''
from flask import Flask
from os import path
from datetime import date as dt
from datetime import datetime
from jinja2 import Environment, PackageLoader, select_autoescape

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'THISISTHESECRETKEY'

    env = Environment(          #Jinja env
        loader=PackageLoader("sd_app"),
        autoescape=select_autoescape()
    )

    keys={}
    with open('keys.txt', 'r') as f:
        key_list = f.readlines()
    keys['openai_key'] = key_list[0]
    keys['youtube_key'] = key_list[1]
    

    from .views import views

    app.register_blueprint(views, url_prefix='/')

    return app
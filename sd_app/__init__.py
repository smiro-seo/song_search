from flask import Flask
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

    from .views import views

    app.register_blueprint(views, url_prefix='/')

    return app
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from datetime import date as dt
from os import path
from flask_login import LoginManager
from datetime import datetime
from jinja2 import Environment, PackageLoader, select_autoescape
from .migrations import check_db_version, set_db_version_current
from .constants import db_string_conn, DB_NAME, database_path

db = SQLAlchemy()


def create_app():
    global app
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'THISISTHESECRETKEY'
    app.config['SQLALCHEMY_DATABASE_URI'] = db_string_conn
    db.init_app(app)

    env = Environment(  # Jinja env
        loader=PackageLoader("sd_app"),
        autoescape=select_autoescape()
    )

    from .views import views
    from .auth import auth
    from .api import api

    app.register_blueprint(views, url_prefix='/')
    app.register_blueprint(auth, url_prefix='/')
    app.register_blueprint(api, url_prefix='/api/')

    from .models import User

    create_database(app)

    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(id):
        return User.query.get(int(id))

    return app


def create_database(app):
    if not path.exists(f'{database_path}/{DB_NAME}'):
        with app.app_context():
            db.create_all()
            set_db_version_current()
        print('Created Database!')
    
    check_db_version()

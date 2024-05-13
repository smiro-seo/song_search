from flask import Flask
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from datetime import date as dt
from os import path
from flask_login import LoginManager
from flask_admin import Admin
from datetime import datetime
from jinja2 import Environment, PackageLoader, select_autoescape
from .migrations import check_db_version, set_db_version_current
from .constants import db_string_conn, DB_NAME, database_path, keys
from flask_admin.contrib.sqla import ModelView


db = SQLAlchemy()
admin = Admin()




def create_app():
    global app
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'THISISTHESECRETKEY'
    app.config['SQLALCHEMY_DATABASE_URI'] = db_string_conn
    db.init_app(app)
    migrate = Migrate(app, db)
    admin.init_app(app)

    setup_admin()


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


# Add your models to Flask Admin
def setup_admin():
    from .models import User, Search, SpotifyDraft

    admin.add_view(ModelView(User, db.session))
    admin.add_view(ModelView(Search, db.session))  
    admin.add_view(ModelView(SpotifyDraft, db.session))

# Call setup_admin() after creating the app
#setup_admin()
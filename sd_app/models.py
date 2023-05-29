from . import db
from flask_login import UserMixin
from sqlalchemy.sql import func


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True)
    password = db.Column(db.String(150))

    searches = db.relationship("Search", back_populates="user_inst")


class Search(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.DateTime(timezone=True), default=func.now())
    user = db.Column(db.String(150))
    keywords = db.Column(db.String(150))
    csv_path = db.Column(db.String(150))
    html_path = db.Column(db.String(150))
    prompt = db.Column(db.String(516))
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    by_artist = db.Column(db.Integer, default=0)

    user_inst = db.relationship("User", back_populates="searches")

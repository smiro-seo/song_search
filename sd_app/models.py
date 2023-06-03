from . import db
from flask_login import UserMixin, current_user
from sqlalchemy.sql import func


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True)
    password = db.Column(db.String(150))
    default_prompt = db.Column(db.String(512))
    default_prompt_artist = db.Column(db.String(512))
    default_intro_prompt = db.Column(db.String(512))
    default_intro_prompt_artist = db.Column(db.String(512))

    searches = db.relationship("Search", back_populates="user_inst")

    def dict_data(self):
        return {
            'username': self.username,
            'default_prompt': self.default_prompt,
            'default_prompt_artist': self.default_prompt_artist,
            'default_intro_prompt': self.default_intro_prompt,
            'default_intro_prompt_artist': self.default_intro_prompt_artist,
            'is_authenticated': current_user.is_authenticated and current_user.id == self.id
        }


class Search(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.DateTime(timezone=True), default=func.now())
    user = db.Column(db.String(150))
    keywords = db.Column(db.String(150))
    status = db.Column(db.String(150))
    prompt = db.Column(db.String(516))
    intro_prompt = db.Column(db.String(516))
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    by_artist = db.Column(db.Integer, default=0)

    user_inst = db.relationship("User", back_populates="searches")

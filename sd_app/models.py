from . import db
from flask_login import UserMixin, current_user
from sqlalchemy.sql import func
from .constants import default_prompt, default_intro_prompt, default_intro_prompt_artist, default_improver_prompt
import json



class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True)
    password = db.Column(db.String(150))
    default_prompt = db.Column(db.String(512))
    default_prompt_artist = db.Column(db.String(512))
    default_intro_prompt = db.Column(db.String(512))
    default_intro_prompt_artist = db.Column(db.String(512))
    default_improver_prompt = db.Column(db.String(512))
    default_img_prompt = db.Column(db.String(512))

    searches = db.relationship("Search", back_populates="user_inst")

    def __init__(self, username, password):
        self.username = username
        self.password = password

        self.default_prompt = default_prompt
        self.default_prompt_artist = default_prompt
        self.default_intro_prompt = default_intro_prompt
        self.default_intro_prompt_artist = default_intro_prompt_artist
        self.default_improver_prompt = default_improver_prompt

    def dict_data(self):
        return {
            'id':self.id,
            'username': self.username,
            'default_prompt': self.default_prompt,
            'default_prompt_artist': self.default_prompt_artist,
            'default_intro_prompt': self.default_intro_prompt,
            'default_intro_prompt_artist': self.default_intro_prompt_artist,
            'default_improver_prompt': self.default_improver_prompt,
            'default_img_prompt': self.default_img_prompt,
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
    improver_prompt = db.Column(db.String(516))
    img_prompt = db.Column(db.String(516))

    image_prompt_keywords_str = db.Column(db.String(516))
    image_nprompt_keywords_str = db.Column(db.String(516))

    model = db.Column(db.String(64))
    improved_song = db.Column(db.Boolean)
    improved_intro = db.Column(db.Boolean)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    by = db.Column(db.String(32), default=0)

    user_inst = db.relationship("User", back_populates="searches")

    @property
    def sp_keywords(self):
        if self.by=="artist": return ""
        kws = json.loads(self.keywords)
        return kws.get('sp_keywords', [])
    @property
    def keyword(self):
        if self.by=="artist": return ""
        kws = json.loads(self.keywords)
        return kws.get('keyword', '')
    @property
    def artist(self):
        if self.by=="keyword": return ""
        return self.keywords
        
    @property
    def image_prompt_keywords(self):
        return json.loads(self.image_prompt_keywords_str)
    @property
    def image_nprompt_keywords(self):
        return json.loads(self.image_nprompt_keywords_str)

    def json_data(self):
        
        if self.by=='artist':
            keywords = self.keywords
        elif self.by=='keyword':
            keywords = self.keyword + " (" + ", ".join(self.sp_keywords) + ")"

        model_name = {
            'gpt-3.5-turbo': 'GPT 3.5 Turbo',
            'text-davinci-003':'DaVinci 3'
        }

        model = self.model
        for p, n in model_name.items():
            model = model.replace(p,n)
            
        data = {
            'id':self.id,
            'date': self.date.strftime("%Y-%m-%d %H:%M"),
            'user': self.user,
            'status':self.status,
            'keywords': keywords,
            'prompt': self.prompt,
            'intro-prompt': self.intro_prompt,
            'improver-prompt': self.improver_prompt,
            'img-prompt': self.img_prompt,
            'improved_song': self.improved_song,
            'improved_intro': self.improved_intro,
            'p-img-keywords': ", ".join(self.image_prompt_keywords),
            'n-img-keywords': ", ".join(self.image_nprompt_keywords),
            'model': model,
            'by':self.by.title()
        }

        return json.dumps(data)


class Parameters(db.Model):
    name = db.Column(db.String(150), primary_key=True)
    value = db.Column(db.String(150))

    @classmethod
    def find(name, default_value=""):
        exists = Parameters.query.get(name)
        if exists:
            return exists.value
        else:
            new_parameter = Parameters(name=name, value=default_value)
            return new_parameter.value
    
    
    @classmethod
    def set(name, value):
        exists = Parameters.query.get(name)
        if exists:
            exists.value = value
        else:
            new_parameter = Parameters(name=name, value=value)
        
        return


class Def_Search():
    def __init__(self, current_user, by):
        self.improver_prompt = current_user.default_improver_prompt
        self.img_prompt = current_user.default_img_prompt
        self.by = by

        if by=="artist":
            self.intro_prompt = current_user.default_intro_prompt_artist
            self.prompt = current_user.default_prompt_artist
        elif by=="keyword":
            self.intro_prompt = current_user.default_intro_prompt
            self.prompt = current_user.default_prompt
        
        self.improved_intro = True,
        self.improved_song=True
        self.artist=""
        self.keyword=""
        self.sp_keywords=""
        self.model='gpt-3.5-turbo'
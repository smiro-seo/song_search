import os
local=True
keys = {}

keys['openai_key'] = os.getenv('OPENAI_API_KEY')
keys['youtube_key'] = os.getenv('YOUTUBE_KEY')
keys['sp_user'] = os.getenv('SPOTIFY_USER')
keys['sp_password'] = os.getenv('SPOTIFY_PASSWORD')
keys['wp_user'] = os.getenv('WP_USERNAME')
keys['wp_password'] = os.getenv('WP_PASSWORD')
keys['sd_key'] = os.getenv('SD_KEY')

default_prompt = 'Write a simple text presenting the song [track name] by [artist] from [release year] describing how it sounds, the feeling of the song, and its meaning. The text should be at least 70 words but no longer than 100 words written in easy-to-understand language. Do not use any quotation marks in the text.'

default_intro_prompt = "Write a simple, interesting and captivating introduction for an article that describes the best songs about [keyword]. The text should be at least 70 words but no longer than 100 words written in easy-to-understand language. Do not use any quotation marks in the text."
default_intro_prompt_artist = "Write a simple, interesting and captivating introduction for an article that describes the best songs from [artist]. The text should be at least 70 words but no longer than 100 words written in easy-to-understand language. Do not use any quotation marks in the text."
default_improver_prompt = ""

DB_NAME = "database.db"
database_path="/opt/var/song_search" if not local else "instance"
db_string_conn = f"sqlite:///{database_path}/{DB_NAME}" if not local else f"sqlite:///{DB_NAME}"
default_model = 'gpt-4o'

aspect_ratios = [
    '16:9', 
'21:9',
'2:3',
'3:2',
'4:5',
'5:4',
'9:16',
'9:21',
]

'''
OLD ASPECT RATIOS
aspect_ratios = [
    ('1024x1024', '1:1'),
    ('1152x896','9:7'),
    ('896x1152', '7:9'),
    ('1216x832', '19:13'),
    ('832x216', '3.85:1'),
    ('1344x768', '7:4'),
    ('768x1344','4:7'),
    ('1536x640', '12:5'),
    ('640x1536', '5:12'),
    ('512x512', '1:1')
]

'''


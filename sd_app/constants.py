import os

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
db_string_conn = f"sqlite:///{DB_NAME}"
default_model = 'text-davinci-003'
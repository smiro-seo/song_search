import os

keys = {}

keys['openai_key'] = os.getenv('OPENAI_KEY')
keys['youtube_key'] = os.getenv('YOUTUBE_KEY')
keys['wp_user'] = os.getenv('WP_USERNAME')
keys['wp_password'] = os.getenv('WP_PASSWORD')

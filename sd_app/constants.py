import os

keys = {}

keys['openai_key'] = os.getenv('OPENAI_KEY')
keys['youtube_key'] = os.getenv('YOUTUBE_KEY')
keys['wp_user'] = os.getenv('WP_USERNAME')
keys['wp_password'] = os.getenv('WP_PASSWORD')

default_prompt = 'Write a simple text presenting the song [track name] by [artist] from [release year] describing how it sounds, the feeling of the song, and its meaning. The text should be at least 70 words but no longer than 100 words written in easy-to-understand language. Do not use any quotation marks in the text.'

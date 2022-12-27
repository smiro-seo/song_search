import os

keys={}
with open(os.path.join(__file__,'keys.txt'), 'r') as f:
    key_list = f.readlines()
keys['openai_key'] = key_list[0]
keys['youtube_key'] = key_list[1]
import os
from pathlib import Path

keys={}
with open(os.path.join(Path(__file__).parent.absolute(),'keys.txt'), 'r') as f:
    key_list = f.readlines()
keys['openai_key'] = str(key_list[0]).strip()
keys['youtube_key'] = key_list[1]
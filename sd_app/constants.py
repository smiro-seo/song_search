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

default_prompt = 'Write a brief descriptive text about the song [track name] by [artist] from [release year]. For the second paragraph, pick a number between 1-14 and write and about the corresponding point in the list below. Make sure the topic in the point is appropriate for the song, if not pick a new random number. Ideas for things you can include in the text: 
1. Genre and Style: Describe the genre and stylistic elements. 
2. Theme and Lyrics: Overview of the theme and key lyrics. 
3. Musical Composition: Instruments and arrangement details. 
4. Production Quality: Production techniques and sound quality. 
5. Inspirations and Influences: Influences behind the song. 
6. Reception and Impact: Fan and critic reception, awards. 
7. Music Video: Concept and style of the music video. 
8. Personal Interpretation: Personal take on the song's impact. 
9. Memorable Moments: Standout sections of the song. 
10. Collaborations: Notable featured artists or producers. 
11. Live Performances: Description of live performances. 
12. Cultural References: Societal issues or cultural references. 
13. Covers and Remixes: Popular covers or remixes. 
14. Interesting facts: For example, if the song won any notable awards or records.

### [Answer in plain English with short sentences] 
### [Apply Hemingway's rules of writing] 
### [Speak like a 30-year-old but don't mention it] 
### [Split the text into two short paragraphs] 
### [Each paragraph can be three sentences at most] 
### [Do not use any quotation marks in the text] 
### [Be creative will you text] 
### [Add semantic entities] 
### [Avoid starting paragraphs with transitional adverbs like 'however, moreover,’ and ‘furthermore'] 
### [Use direct transitions instead and apply varied sentence structures in the process] 
### [Use contractions to sound more conversational] 
### [Replace commonly used words and phrases with synonyms] 
### [Eliminate all use of the following words; Delve, Plethora, Realm]
'

default_intro_prompt = "Write a simple, interesting, and captivating introduction for an article listing the best songs about [keyword]. Mention how [keyword] is represented in music and any notable artists that have written songs about [keyword].

### [Answer in plain English with short sentences] 
### [Apply Hemingway's rules of writing] 
### [Speak like a 30-year-old but don't mention it] 
### [Split the text into two short paragraphs] 
### [Each paragraph can be three sentences at most] 
### [Do not use any quotation marks in the text] 
### [Be creative will you text] 
### [Add semantic entities] 
### [Avoid starting paragraphs with transitional adverbs like 'however, moreover,’ and ‘furthermore'] 
### [Use direct transitions instead and apply varied sentence structures in the process]
"

default_intro_prompt_artist = "Write a simple, interesting, and captivating introduction for an article that describes the best songs from [artist]. Mention what's unique about the artists' music, and any notable collaborations they have had with other artists.

### [Answer in plain English with short sentences] 
### [Apply Hemingway's rules of writing] 
### [Speak like a 30-year-old but don't mention it] 
### [Split the text into two short paragraphs] 
### [Each paragraph can be three sentences at most] 
### [Do not use any quotation marks in the text] 
### [Be creative will you text] 
### [Add semantic entities] 
### [Avoid starting paragraphs with transitional adverbs like 'however, moreover,’ and ‘furthermore'] 
### [Use direct transitions instead and apply varied sentence structures in the process]
### [Replace commonly used words and phrases with synonyms]
### [Eliminate all use of the following words; Delve, Plethora, Realm]
"
default_improver_prompt = ""

DB_NAME = "database.db"
database_path="/opt/var/song_search" if not local else "instance"
db_string_conn = f"sqlite:///{database_path}/{DB_NAME}" if not local else f"sqlite:///{DB_NAME}"
default_model = 'gpt-4o'

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

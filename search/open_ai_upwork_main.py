
import argparse, json, os, pathlib, string, time, spotipy, re
from datetime import datetime
from uuid import uuid4
import pandas as pd
from spotipy.oauth2 import SpotifyClientCredentials
from googleapiclient.errors import HttpError
import urllib.request
import urllib.parse
from .html_generator import generate_html
from .wordpress import create_wp_draft, add_wp_image
from .ai import Model_Generator
from .search_youtube import youtube_search

market = 'US'
# Characters after which the track name does not matter for duplicates
flagged_characters = ['-', '(', '/']
   

column_list = ['artist', 'track_name', 'release_year', 'album', 'yt_video_id',
               'model_response', 'popularity', 'duration_ms', 'track_id']
column_name_transform = {'artist': 'Artist', 'track_name': 'Track Name',
                         'release_year': 'Release Year', 'album': 'Album'}
cwd = os.path.dirname(__file__)

# define auth keys
youtube_api_key = ''

# paths
path = os.path.join(cwd,'..', '..', '..', '..', 'var', 'song_search', 'model_outputs')


def search_spotify_tracks(keyword, sp, target="track", by="track", keyword_id=None):
    search_columns = ['artist', 'track_name', 'release_year',
                      'album', 'popularity', 'duration_ms', 'track_id', 'spotify_url']

    def clean_names_for_list(track_name, keyword):
        '''
            This function cleans the name of the track in order to avoid substrings and names of additional artists.
            Example: "Perfect (Remix) (feat. Doja Cat & BIA)" comes up when searching for "Cat"
            By applying this function, that track would come up as only "Perfect", so it would not appear in the search results
        '''
        start = min([track_name.find(c) for c in flagged_characters])
        if start != -1:
            track_name = track_name[:start]

        n_words_kw = len(keyword.split(' '))
        track_name_wlist = track_name.lower().split(' ')

        if n_words_kw <= 1:
            return track_name_wlist

        else:
            n_words_tn = len(track_name_wlist)
            track_name_wlist = track_name.lower().split(' ')
            word_combinations = [
                ' '.join(track_name_wlist[i:i+n_words_kw]) for i in range(0, n_words_tn-1)]
            return word_combinations

    

    search_results_clean = []
    print("Searching for " + target + " by " + by)

    if target == "track":
        total_results = sp.search(q=f'{by}:{keyword}', type=target, limit=1, offset=0)['tracks']['total']

        if total_results == 0:
            # Avoid processing if there are no results
            return pd.DataFrame(columns=search_columns)

        #   Process in batches
        for offset in range(0, total_results-1, 50):
            if offset >= 1000:  # Maximum offset spotipy can handle
                break
                
            track_search_results = sp.search(
                q=f'{by}:{keyword}', type=target, limit=50, offset=offset, market=market)['tracks']['items']
            
            if by=="track":
                track_search_results_clean = [track for track in track_search_results if keyword in clean_names_for_list(
                    track.get('name', None), keyword)]
            else:
                track_search_results_clean=[track for track in track_search_results if keyword_id in [artist['id'] for artist in track['artists']]]
            
            for i, track in enumerate(track_search_results_clean):

                search_results_clean.append({
                    'artist': ', '.join([artist['name'] for artist in track['artists']]),
                    'track_name': track['name'],
                    'release_year': track['album']['release_date'][:4],
                    'album': track['album']['name'],
                    'popularity': track['popularity'],
                    'duration_ms': track['duration_ms'],
                    'track_id': track['id'],
                    'spotify_url': track['external_urls']['spotify']
                })

        df_search_results_clean = pd.DataFrame(
            search_results_clean, columns=search_columns)
        return df_search_results_clean

    if target == "artist":
        search_results = sp.search(
            q=f'artist:{keyword}', type="artist", limit=30, offset=0)['artists']['items']

        
        df_search_results = pd.DataFrame(
            search_results, columns=['id', 'name', 'popularity'])
        return df_search_results


def scrape_youtube_search_results(track_title):
    def is_same_song(song1, song2):
    
        song1_words = set(song1.lower().split())
        song2_words = set(song2.lower().split())
        common_words = song2_words.intersection(song2_words)

        if len(common_words) >= 2:
            return True
        else: return False

    input = urllib.parse.urlencode({'search_query': track_title})
    try:
        html = urllib.request.urlopen(
            "http://www.youtube.com/results?" + input)
        all_results = re.findall(r"watch\?v=(\S{11})", html.read().decode())
        video_id=None
        for song_id in all_results:
            song_html = urllib.request.urlopen("http://www.youtube.com/results?" + song_id)
            yt_title = re.search(r'>(.*?)</title>', song_html, re.DOTALL | re.IGNORECASE)
            if is_same_song(track_title, yt_title):
                video_id=song_id
                break

    except:
        video_id = ''

    return video_id

def get_youtube_search_results(data, stopper):

    if (stopper.is_set()): raise Exception("stopped")

    track_title = f"{data['track_name']} {data['artist']}"

    options = argparse.Namespace(q=track_title, max_results=1)
    try:
        # Try getting the video data from google API
        search_results = youtube_search(options, youtube_api_key)
        video_id = search_results['items'][0]['id']['videoId']
    except HttpError as error:
        # check if the error is due to exceeding the daily quota
        if error.resp.status in [403, 404]:
            # handle the error and switch to scraping solution
            print(
                'Daily quota for YouTube Data API exceeded... Switching to YouTube scraping solution...')
            video_id = scrape_youtube_search_results(track_title)
        else:
            print('There was an error using the YouTube Data API... Switching to YouTube scraping solution...')
            video_id = scrape_youtube_search_results(track_title)
    except Exception as e:
        print('There was an error using the YouTube Data API... Switching to YouTube scraping solution...')
        video_id = scrape_youtube_search_results(track_title)

 #   video_url = f'https://www.youtube.com/watch?v={video_id}'
    return video_id

def cleanse_track_duplicates(df):
    def delete_after_character(track_name):
        for c in flagged_characters:
            end = track_name.find(c)
            if end != -1:
                track_name = track_name[:end-1]
        return track_name

    # Use clean track names
    df['track_name_clean'] = df.apply(
        lambda x: delete_after_character(x['track_name']), axis=1)

    df.drop_duplicates(subset='track_name_clean', keep='first', inplace=True)
    print(df[['track_name', 'popularity']])
    return df

def clean_and_sort(df):
    # Order by most popular songs (total)
    df.sort_values('popularity', ascending=False, inplace=True)

    #   Keeping only the relevant columns
    df_relevant = df[column_list]

    df_clean = df_relevant.rename(columns=column_name_transform)
    df_clean.reset_index(inplace=True)
    return df_clean


def generate_html_file(html):
    output_html_name = f'sample_keywords_output_html_{datetime.now().strftime("%Y%m%d-%H%M%S")}.html'
    output_dir = os.path.join(cwd, '..', '..', '..', '..', 'var', 'song_search', 'model_outputs')
    output_path = os.path.join(output_dir, output_html_name)

    print(f"Saving HTML file to : {output_path}")

    if not os.path.exists(output_dir):
        os.mkdir(output_dir)
    
    with open(output_path, 'wb') as f:
        f.write('<!DOCTYPE html>'.encode('utf-8'))
        f.write(html.encode('utf-8'))

    return output_html_name


def search_artists(artist_name, keys):
    # instantiate spotify api client
    sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(client_id=keys['sp_user'],
                                                               client_secret=keys['sp_password']))
    artists = search_spotify_tracks(artist_name,sp, target="artist")
    artists.sort_values('popularity', ascending=False, inplace=True)
    return artists


class Search_Process():

    def __init__(self, data, limit_st, offset_res, keys, current_user):

        self.prompt = data.get('prompt', current_user['default_intro_prompt_artist'])
        self.improver_prompt = data.get('improver-prompt', current_user['default_improver_prompt'])
        self.intro_prompt = data.get('intro-prompt', current_user['default_intro_prompt_artist'])

        self.include_img = data.get('include-img', False)

        if self.include_img:
            self.img_prompt = data.get('img-prompt', current_user['default_img_prompt'])
            self.image_prompt_keywords = data.get('image-prompt-keywords', [])
            self.image_nprompt_keywords = data.get('image-nprompt-keywords', [])

        else:
            self.img_prompt = ""
            self.image_prompt_keywords = []
            self.image_nprompt_keywords = []

        self.improve_song = data.get('improve-song', False)
        self.improve_intro = data.get('improve-intro', False)

        self.wordpress =  data.get('wordpress', False)
        self.model = data.get('model','gpt-4-1106-preview' )
        
        self.limit = limit_st
        self.offset = offset_res
        self.keys = keys
        
        #   Misc.
        self.keyword_descriptor=""
        self.wp_title=""
        self.slug=""
        self.by=""

        self.record = None
        self.img_config = data.get('img-config', {'steps':30})
 
    def create_record(self, Search, current_user):
        self.record = Search(
            # Create search
            user=current_user['username'],
            user_id=current_user['id'],
            keywords=self.keyword_descriptor,
            status="In progress",
            prompt=self.prompt,
            intro_prompt=self.intro_prompt,
            improver_prompt=self.improver_prompt,
            model=self.model,
            by=self.by,
            improved_song=self.improve_song,
            improved_intro=self.improve_intro,

            include_img=self.include_img,
            img_prompt=self.img_prompt,
            image_prompt_keywords_str=json.dumps(self.image_prompt_keywords),
            image_nprompt_keywords_str=json.dumps(self.image_nprompt_keywords),
            img_config_str=json.dumps(self.img_config)

        )

        return self.record

    def run(self, flag_running, stopper):

        try:
            # instantiate spotify api client
            self.sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(client_id=self.keys['sp_user'],client_secret=self.keys['sp_password']),requests_timeout=60)
            self.main_process(stopper)

            flag_running.clear()
            stopper.clear()

            return "Completed"
        
        except Exception as e:

            flag_running.clear()
            stopper.clear()

            if str(e)=="stopped":
                print("Search stopped")
                return "Stopped"
            else:
                print("Error while running search")
                print(e)
                return "Failed"

    def wp_draft(self, html, img_binary=None, img_name=''):
        
        img_id=None
        if img_binary is not None:
            if img_name=='': img_name='fet_img_' + self.slug.replace('-', '_')
            img_id = add_wp_image(img_binary, img_name, self.keys)

        create_wp_draft(self.wp_title, html, self.slug, self.keys, img_id)

    def main_process(self, stopper):

        youtube_api_key = self.keys['youtube_key']
        generator = Model_Generator(self, self.keys)

        #   Get spotify data
        result_df = self.get_search_results(stopper)
        if not isinstance(result_df, pd.DataFrame): return False

        #   Get youtube data
        print(f"Getting Youtube data")
        for i, track in result_df.iterrows(): result_df.loc[i, 'yt_video_id']=get_youtube_search_results(track, stopper)

        #   Get openai data
        print(f"Getting OpenAI response")
        for i, track in result_df.iterrows(): result_df.loc[i, 'model_response']=generator.song_description(track, stopper)


        #   Clean and sort results
        clean_data = clean_and_sort(result_df)

        #   Generate intro
        intro = generator.intro()

        #   Create html
        print("Getting HTML")
        html, self.full_text = generate_html(clean_data, intro, return_full_text=True)
        #   Generate feat. image
        if self.include_img:
            print("Getting featured image")
            if self.record is None: filename=None
            else: filename = json.loads(self.record.json_data())['img_name']

            img_binary, img_name, img_gen_prompt = generator.feat_image(filename=filename)
            self.record.img_gen_prompt = img_gen_prompt
        else:
            img_binary=None
            img_name=None

        #   Post to wp
        if self.wordpress: 
            self.wp_draft(html, img_binary, img_name)
        output_html_name = generate_html_file(html)

        return True


class Search_Keyword(Search_Process):


    def __init__(self, data, limit_st, offset_res, keys, current_user):
        Search_Process.__init__(self, data, limit_st, offset_res, keys, current_user)
        self.by="keyword"
        self.sp_keywords=data.get('sp_keywords', [])
        self.keyword = data.get('keyword', '')
        self.keyword_descriptor = json.dumps({'keyword': self.keyword, 'sp_keywords':self.sp_keywords})

        self.intro_prompt = self.intro_prompt.replace('[keyword]', self.keyword)
        self.img_prompt = self.img_prompt.replace('[artist]', self.keyword).replace('[keyword]', self.keyword)
        self.values_to_replace = {'[keyword]': self.keyword}

        #   Title and slug
        self.slug = 'songs-about-' + self.keyword.lower()
        self.wp_title = f'{str(limit_st)} Songs About {self.keyword.title()}'

    
    def get_search_results(self, stopper):
        search_term_dfs = []  # list with search term results

        for keyword in self.sp_keywords:

            if (stopper.is_set()): raise Exception("stopped")
            
            print("|||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||")
            print(f"Starting first keyword: {keyword}")
            print(f'Getting most popular songs containing {keyword}')
            df_w_spot_df = search_spotify_tracks(keyword, self.sp, target="track", by="track")

            search_term_dfs.append(df_w_spot_df)

        # search term-level dataframe
        st_out_sp_df = pd.concat(search_term_dfs)
        st_out_sp_df.sort_values('popularity', ascending=False, inplace=True)
        if st_out_sp_df.shape[0] == 0: return st_out_sp_df


        # drop duplicates
        print("Dropping duplicates")
        out_df_no_duplicates = cleanse_track_duplicates(st_out_sp_df)
        if self.limit != -1:
            if out_df_no_duplicates.shape[0] > self.offset + self.limit:
                # search_term-level filtering
                out_df_no_duplicates = out_df_no_duplicates.iloc[self.offset:self.offset + self.limit]
            elif out_df_no_duplicates.shape[0] > self.offset:
                out_df_no_duplicates = out_df_no_duplicates.iloc[self.offset:]
            else:
                print(f"Offset too big for results. Returning empty table.")
                out_df_no_duplicates = pd.DataFrame(columns=out_df_no_duplicates.columns)

        print("Prepping our KW output...")
        # prep for final output
        out_df = out_df_no_duplicates.copy()

        return out_df


class Search_Artist(Search_Process):


    def __init__(self, data, limit_st, offset_res, keys, current_user):
        Search_Process.__init__(self, data, limit_st, offset_res, keys, current_user)
        self.by="artist"

        self.artist_name=data.get('artist-name', None)
        self.artist_id=data.get('artist-id', None)

        self.intro_prompt = self.intro_prompt.replace('[artist]', self.artist_name)
        self.img_prompt = self.img_prompt.replace('[artist]', self.artist_name).replace('[keyword]', self.artist_name)
        
        self.keyword_descriptor=self.artist_name
        self.values_to_replace = {'artist':self.artist_name}

        #   Title and slug
        self.slug = self.artist_name.replace(" ", "-").lower() + "-songs"
        self.wp_title = f'{limit_st} Best {self.artist_name.title()} Songs'
    
    def get_search_results(self, stopper):

        if (stopper.is_set()): raise Exception("stopped")

        print("|||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||")
        print(f"Searching for top songs by {self.artist_name}")
        df_w_spot_df = search_spotify_tracks(self.artist_name, self.sp, target="track", by="artist", keyword_id=self.artist_id)

        df_w_spot_df.sort_values('popularity', ascending=False, inplace=True)
        print("Limiting search results to " + str(self.limit))

        # drop duplicates
        print("Dropping duplicates")
        df_w_spot_df = cleanse_track_duplicates(df_w_spot_df)
        if self.limit != -1:
            if df_w_spot_df.shape[0] > self.offset + self.limit:
                # search_term-level filtering
                df_w_spot_df = df_w_spot_df.iloc[self.offset:self.offset + self.limit]
            elif df_w_spot_df.shape[0] > self.offset:
                df_w_spot_df = df_w_spot_df.iloc[self.offset:]
            else:
                print(f"Offset too big for results. Returning empty table.")
                df_w_spot_df = pd.DataFrame(columns=df_w_spot_df.columns)

        return df_w_spot_df

    

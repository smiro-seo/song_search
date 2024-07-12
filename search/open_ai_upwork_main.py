
import argparse, json, os, pathlib, string, time, spotipy, re
from datetime import datetime
from uuid import uuid4
import pandas as pd
from spotipy.oauth2 import SpotifyClientCredentials
from googleapiclient.errors import HttpError
import urllib.request
import urllib.parse

from sd_app.models import SpotifyDraft
from .html_generator import generate_html
from .wordpress import create_wp_draft, add_wp_image
from .ai import Model_Generator, local
from .search_youtube import youtube_search
from sd_app.constants import keys 



market = 'US'
# Characters after which the track name does not matter for duplicates
flagged_characters = ['-', '(', '/', '{', '[']
   

column_list = ['artist', 'track_name', 'release_year', 'yt_video_id',
               'model_response', 'popularity', 'duration_ms', 'track_id']
column_name_transform = {'artist': 'Artist', 'track_name': 'Track Name',
                         'release_year': 'Release Year'}
cwd = os.path.dirname(__file__)

# define auth keys
youtube_api_key = keys["youtube_key"]

# paths
path = os.path.join(cwd,'..', '..', '..', '..', 'var', 'song_search', 'model_outputs') if not local else os.path.join(cwd,'model_outputs')

def clean_name(name):
    new_name = name.replace(' ', '_').replace('-', '_').replace('(', '').replace(')', '').replace('.', '').replace(',', '')
    return new_name

def search_spotify_tracks(keyword, sp, target="track", by="track", keyword_id=None):
    search_columns = ['artist', 'track_name', 'release_year',
                      'album', 'popularity', 'duration_ms', 'track_id', 'spotify_url']

    def clean_names_for_list(track_name, keyword):

        '''
            This function cleans the name of the track in order to avoid substrings and names of additional artists.
            Example: "Perfect (Remix) (feat. Doja Cat & BIA)" comes up when searching for "Cat"
            By applying this function, that track would be excluded unless the keyword is in the song title only
        '''

        track_name = str(track_name).lower() 
        keyword = keyword.lower()  
        
        # Find the first occurrence of any flagged character
        start_positions = [track_name.find(c) for c in flagged_characters if track_name.find(c) != -1]
        
        # Set start to the position of the earliest flagged character or -1 if none are found
        start = min(start_positions) if start_positions else -1
        
        # Find the position of the keyword
        keyword_pos = track_name.find(keyword)
        print("start:", start, "keyword_pos:", keyword_pos)
        
        # If the keyword is not found or it is found after the first flagged character, remove the track
        if keyword_pos == -1 or (start != -1 and keyword_pos > start):
            return False
        
        n_words_kw = len(keyword.split(' '))
        track_name_wlist = track_name.split(' ')

        if n_words_kw <= 1:
            word_combinations = track_name_wlist
        else:
            n_words_tn = len(track_name_wlist)
            word_combinations = [
                ' '.join(track_name_wlist[i:i+n_words_kw]) for i in range(n_words_tn - n_words_kw + 1)
            ]

        # Check if the keyword is in any of the word combinations
        keyword_in_combinations = any(keyword in combination for combination in word_combinations)
        
        if keyword_in_combinations:
            return True
        else:
            return False
        
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
                track_search_results_clean = [track for track in track_search_results if clean_names_for_list(track.get('name', None), keyword)]    
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
        common_words = song1_words.intersection(song2_words)

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
            song_html = urllib.request.urlopen("http://www.youtube.com/watch?v=" + song_id)
            yt_title = re.findall(r'<title>(.*?)</title>', song_html.read().decode())[0]

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
    output_dir = os.path.join(cwd, '..', '..', '..', '..', 'var', 'song_search', 'model_outputs') if not local else os.path.join(cwd,'model_outputs')
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
        self.model = data.get('model','gpt-4o' )
        
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
            intro_prompt=self.intro_prompt_original,
            improver_prompt=self.improver_prompt,
            model=self.model,
            by=self.by,
            improved_song=self.improve_song,
            improved_intro=self.improve_intro,

            include_img=self.include_img,
            img_prompt=self.img_prompt_original,
            image_prompt_keywords_str=json.dumps(self.image_prompt_keywords),
            image_nprompt_keywords_str=json.dumps(self.image_nprompt_keywords),
            img_config_str=json.dumps(self.img_config)

        )

        return self.record
   
    def run(self, flag_running, stopper):

        try:
            # instantiate spotify api client
            print("hi I am running", stopper)
            self.sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(client_id=keys['sp_user'],client_secret=keys['sp_password']),requests_timeout=60)
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

        create_wp_draft(self.wp_title, html, self.slug, self.keys, img_id, by=self.by)

    def main_process(self, stopper):

        youtube_api_key = self.keys['youtube_key']
        generator = Model_Generator(self, self.keys)

        #   Get spotify data
        result_df = self.get_search_results(stopper)
        spotify_drafts_dicts = [obj.__dict__ for obj in result_df]
        result_df = pd.DataFrame(spotify_drafts_dicts)


        print('print result df',result_df)
        if not isinstance(result_df, pd.DataFrame): return False


        #   Get youtube data
        print(f"Getting Youtube data")
        for i, track in result_df.iterrows():
            yt_video_id = get_youtube_search_results(track, stopper)
            print('yt',yt_video_id)
            result_df.loc[i, 'yt_video_id'] = yt_video_id
        
        #get the first track in the resultdf
        first_row = result_df.iloc[0]

        print("here is the first song", first_row)
        self.intro_prompt = self.intro_prompt.replace('[keyword]',self.keyword)
        self.img_prompt = self.img_prompt.replace('[artist]',first_row.artist).replace('[keyword]',self.keyword)


        print( 'prompts',self.intro_prompt, self.img_prompt, self.values_to_replace )

        #   Get openai data
        print(f"Getting OpenAI response")
        for i, track in result_df.iterrows():  
            try:
                self.values_to_replace = {'[keyword]':self.keyword}
                model_response = generator.song_description(track, stopper)
                print('model response',model_response)
                print('intro_prompt', self.intro_prompt)
                print("img_prompt", self.img_prompt)
                print("values_to_replace", self.values_to_replace)
                
                result_df.loc[i, 'model_response'] = model_response
            except Exception as e:
                print("model error", e)
            
        
        print("result_df",result_df)
        #   Clean and sort results
        clean_data = clean_and_sort(result_df)

        #   Generate intro
        intro = generator.intro()

        #   Create html
        print("Getting HTML")
        try:
            html, self.full_text = generate_html(clean_data, intro, return_full_text=True)
        except Exception as e:
            print('error while generating html',e)
            

         #   Generate feat. image
        try:
            if self.include_img:
                print("Getting featured image")
                print(self.__dict__)
                if self.by=='keyword': 
                    img_name = "songs_about_" + clean_name(self.keyword_descriptor)

                if self.by=='artist': 
                    img_name = clean_name(self.keyword_descriptor) + "_songs"

                if self.record is None: filename=None
                else: filename = img_name

                print("file_name: " + filename)
                img_binary, img_name, img_gen_prompt, seed = generator.feat_image(filename=filename)
                self.record.img_gen_prompt = img_gen_prompt
                self.record.img_config['seed']=seed
                self.img_config['seed']=seed

            else:
                img_binary=None
                img_name=None
        except Exception as e:
            print('error while generating feat. image',e)


        #   Post to wp
        try:
            if self.wordpress: 
                self.wp_draft(html, img_binary, img_name)
        except Exception as e:
            print('error while posting to wordpress',e)
        
        #remove all drafts
        try:
            if self.by=='keyword':
                SpotifyDraft.query.filter(SpotifyDraft.searchedby.contains('keyword')).delete(synchronize_session=False)
            if self.by=='artist':
                SpotifyDraft.query.filter(SpotifyDraft.searchedby.contains('artist')).delete(synchronize_session=False)
        except Exception as e:
            print('error while deleting drafts',e)

        try:
            output_html_name = generate_html_file(html)
        except Exception as e:
            print('error while generating html file',e)
        # delete all 

        return True

class Search_Spotify():
    def __init__(self, data, limit_st, offset_res, keys,searchedby):
        print("while init search spotify")
        print(data)
        self.limit = limit_st
        self.offset = offset_res
        self.keys = keys
        self.searchedby = searchedby
        self.artist = '',
        self.track_name = '',
        self.by= searchedby
        self.sp_keywords=data.get('sp_keywords', [])
        self.keyword = data.get('keyword', '')
        self.keyword_descriptor = json.dumps({'keyword': self.keyword, 'sp_keywords':self.sp_keywords})
        

    def create_spotify_draft(self, SpotifyDraft, current_user, artist,track_name,searchedby):

        try:
            self.record = SpotifyDraft(
                #create_spotify_draft
                user=current_user['username'],
                #user_id=current_user['id'],
                searchedby = searchedby,
                artist=artist,
                track_name=track_name,
            )
        except Exception as e:
            print('erro on create',e)
            #return False

        return self.record

    def main_process(self,stopper):
        result_df = self.get_search_results(stopper)
        print(result_df)
        # if not isinstance(result_df, pd.DataFrame): return False

        # #   Clean and sort results
        #clean_data = clean_and_sort(result_df)

        return result_df
    
    def run(self, flag_running, stopper):
        try:
            # instantiate spotify api client
            self.sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(client_id=keys['sp_user'],client_secret=keys['sp_password']),requests_timeout=60)
            spotify_results = self.main_process(stopper)

            flag_running.clear()
            stopper.clear()

            print("whle posting", spotify_results)

            return spotify_results
        
        except Exception as e:

            flag_running.clear()
            stopper.clear()

            if str(e)=="stopped":
                print("Search stopped")
                return "Stopped"
            else:
                print("Error while running search keyword")
                print(e)
                return "Failed"
    
    
class Search_Keyword(Search_Process):

    def __init__(self, data, limit_st, offset_res, keys, current_user, by):
        Search_Process.__init__(self, data, limit_st, offset_res, keys, current_user)
        self.by=by
        self.sp_keywords=data.get('sp_keywords', [])
        self.keyword = data.get('keyword', '')
        self.keyword_descriptor = json.dumps({'keyword': self.keyword, 'sp_keywords':self.sp_keywords})

        self.intro_prompt_original = self.intro_prompt
        self.img_prompt_original = self.img_prompt
        # self.intro_prompt = self.intro_prompt.replace('[keyword]', self.keyword)
        # self.img_prompt = self.img_prompt.replace('[artist]', self.keyword).replace('[keyword]', self.keyword)
        # self.intro_prompt = ''
        # self.img_prompt = ''
        self.values_to_replace = {'[keyword]': self.keyword}
        self.summary = data.get('summary', "")

        #   Title and slug
        # self.slug = 'songs-about-' + self.keyword.lower()
        # self.wp_title = f'{str(limit_st)} Songs About {self.keyword.title()}'
        self.slug = ''
        self.wp_title = ''
    
    def get_search_results(self, stopper):
        songs =SpotifyDraft.query.filter(SpotifyDraft.searchedby.contains('keyword')).order_by(SpotifyDraft.date.desc()).all()

        if (stopper.is_set()): raise Exception("stopped")

        first_song = songs[0]
        artist = first_song.__dict__['artist']
        #keyword = first_song.__dict__['keyword']
        keyword = self.keyword
        artist = str(artist)
        keyword = str(keyword)
        print("searching the keyword", keyword)

        self.intro_prompt = self.intro_prompt.replace('[keyword]', keyword)
        self.img_prompt = self.img_prompt.replace('[artist]', artist).replace('[keyword]', keyword)

        # from song pick the first one
        self.slug = 'songs-about-' + self.keyword
        self.wp_title = f'{str(len(songs))} Songs About {self.keyword.title()}'
        return songs

class Search_Artist(Search_Process):

    def __init__(self, data, limit_st, offset_res, keys, current_user, by):
        Search_Process.__init__(self, data, limit_st, offset_res, keys, current_user)
        self.by=by

        self.artist_name=data.get('artist-name', '')
        self.artist_id=data.get('artist-id', '')
        self.summary = data.get('summary','')
        self.keyword = data.get('keyword', '')

        self.intro_prompt_original = self.intro_prompt
        self.img_prompt_original = self.img_prompt
        # self.intro_prompt = self.intro_prompt.replace('[artist]', self.artist_name)
        # self.img_prompt = self.img_prompt.replace('[artist]', self.artist_name).replace('[keyword]', self.artist_name)
        # self.intro_prompt
        # self.img_prompt
        
        
        self.keyword_descriptor=self.artist_name
        self.values_to_replace = {'artist':self.artist_name}

        #   Title and slug
        self.slug = ''
        self.wp_title = ''

        self.by = by
    
    def get_search_results(self, stopper):
        print("in getting search")
        try:
            songs = SpotifyDraft.query.filter(SpotifyDraft.searchedby.contains('artist')).order_by(SpotifyDraft.date.desc()).all()
        except Exception as e:
            print('exception on getting result',e)
        # print("such are songs", type(songs),songs)

        #artist = str(songs[0].__dict__['artist'])
        artist = self.artist_name

        print('while getting results',artist)

        self.intro_prompt = self.intro_prompt.replace('[artist]', artist)
        self.img_prompt = self.img_prompt.replace('[artist]', artist)

        self.artist_name = artist.replace(' ', '-').lower()
        self.keyword_descriptor = artist.replace(' ', '-').lower()

        # from song pick the first one
        self.slug = artist.replace(" ", "-").lower() + "-songs"
        self.wp_title = f'{len(songs)} Best {artist.title()} Songs'
        return songs


class Search_Spotify_Keyword(Search_Spotify):

    def __init__(self, data, limit_st, offset_res, keys, current_user):
        Search_Process.__init__(self, data, limit_st, offset_res, keys, current_user)
        self.by="keyword"
        self.sp_keywords=data.get('sp_keywords', [])
        self.keyword = data.get('keyword', '')
        self.keyword_descriptor = json.dumps({'keyword': self.keyword, 'sp_keywords':self.sp_keywords})

        self.intro_prompt_original = self.intro_prompt
        self.img_prompt_original = self.img_prompt
        self.intro_prompt = self.intro_prompt
        self.img_prompt = self.img_prompt
        self.values_to_replace = {'[keyword]': self.keyword}

        #   Title and slug
        self.slug = ""
        self.wp_title = ""
    
    def create_spotify_draft(self, SpotifyDraft, keyword, sp_keywords, current_user,searchedby, artist,track_name, release_year, album, popularity, duration_ms, track_id, spotify_url, track_name_clean):
        try:
            #track_name = re.split("\(feat|\(with", track_name)[0].strip()
            self.record = SpotifyDraft(
                keyword=keyword,
                sp_keywords=sp_keywords,
                #create_spotify_draft
                user=current_user['username'],
                #user_id=current_user['id'],
                searchedby = searchedby,
                artist=artist,
                track_name=track_name,
                release_year = release_year,
                album=album,
                popularity=popularity,
                duration_ms=duration_ms,
                track_id=track_id,
                spotify_url=spotify_url,
                track_name_clean = track_name_clean
            )
        except Exception as e:
            print('erro on create',e)
            #return False

        return self.record
    
    def get_search_results(self, stopper):
        search_term_dfs = []  # list with search term results

        for keyword in self.sp_keywords:

            keyword = keyword.lower()
            print(keyword)

            if (stopper.is_set()): raise Exception("stopped")
            
            print("|||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||")
            print(f"Starting first keyword: {keyword}")
            print(f'Getting most popular songs containing {keyword}')
            df_w_spot_df = search_spotify_tracks(keyword, self.sp, target="track", by="track")
            print('df',df_w_spot_df)

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
        print("Prepping our KW output...", out_df)

        return out_df

    def main_process(self,stopper):
        result_df = self.get_search_results(stopper)
        print('song result',result_df)
        # if not isinstance(result_df, pd.DataFrame): return False

        # #   Clean and sort results
        #clean_data = clean_and_sort(result_df)

        return result_df
    
    def run(self, flag_running, stopper):

        try:
            # instantiate spotify api client
            self.sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(client_id=keys['sp_user'],client_secret=keys['sp_password']),requests_timeout=60)
            spotify_results = self.main_process(stopper)

            flag_running.clear()
            stopper.clear()

            print("whle posting", spotify_results)

            return spotify_results
        
        except Exception as e:

            flag_running.clear()
            stopper.clear()

            if str(e)=="stopped":
                print("Search stopped")
                return "Stopped"
            else:
                print("Error while running search keyword")
                print(e)
                return "Failed"


class Search_Spotify_Artist(Search_Spotify):

    def __init__(self, data, limit_st, offset_res, keys, current_user):
        Search_Process.__init__(self, data, limit_st, offset_res, keys, current_user)
        self.by="artist"

        self.artist_name=data.get('artist-name', None)
        self.artist_id=data.get('artist-id', None)

        self.intro_prompt_original = self.intro_prompt
        self.img_prompt_original = self.img_prompt
        self.intro_prompt = self.intro_prompt
        self.img_prompt = self.img_prompt
        
        self.keyword_descriptor=self.artist_name
        self.values_to_replace = {'artist':self.artist_name}

        #   Title and slug
        self.slug = ""
        self.wp_title = ""
    
    def create_spotify_draft(self, SpotifyDraft,keyword, sp_keywords, current_user,searchedby, artist,track_name, release_year, album, popularity, duration_ms, track_id, spotify_url, track_name_clean):
        try:
            #track_name = re.split("\(feat|\(with", track_name)[0].strip()
            self.record = SpotifyDraft(
                #create_spotify_draft
                keyword=keyword,
                sp_keywords=sp_keywords,
                user=current_user['username'],
                #user_id=current_user['id'],
                searchedby = searchedby,
                artist=artist,
                track_name=track_name,
                release_year = release_year,
                album=album,
                popularity=popularity,
                duration_ms=duration_ms,
                track_id=track_id,
                spotify_url=spotify_url,
                track_name_clean = track_name_clean
            )
        except Exception as e:
            print('erro on create',e)
            #return False

        return self.record
    def get_search_results(self, stopper):

        if (stopper.is_set()): raise Exception("stopped")

        print("|||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||")
        print(f"Searching for top songs by {self.artist_name}")
        df_w_spot_df = search_spotify_tracks(self.artist_name.lower(), self.sp, target="track", by="artist", keyword_id=self.artist_id)

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
    
    def main_process(self,stopper):
        result_df = self.get_search_results(stopper)
        print(result_df)
        # if not isinstance(result_df, pd.DataFrame): return False

        # #   Clean and sort results
        #clean_data = clean_and_sort(result_df)

        return result_df
    
    def run(self, flag_running, stopper):

        try:
            # instantiate spotify api client
            self.sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(client_id=keys['sp_user'],client_secret=keys['sp_password']),requests_timeout=60)
            spotify_results = self.main_process(stopper)

            flag_running.clear()
            stopper.clear()

            print("whle posting", spotify_results)

            return spotify_results
        
        except Exception as e:

            flag_running.clear()
            stopper.clear()

            if str(e)=="stopped":
                print("Search stopped")
                return "Stopped"
            else:
                print("Error while running search keyword")
                print(e)
                return "Failed"


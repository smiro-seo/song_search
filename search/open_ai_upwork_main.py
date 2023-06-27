
import argparse
import json
import functools
import os
import pathlib
import string
from datetime import datetime
from uuid import uuid4
import time
import openai
import pandas as pd
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from googleapiclient.errors import HttpError
import re
import urllib.request
import urllib.parse
from .html_generator import generate_html
from .wordpress import create_wp_draft

local_run = True
gpt_max_tokens = 300

# Top N songs per keyowrd (ex. cat). For all results insert -1
limit_per_keyword = -1
# Top N songs for search term (ex. animals). For all results insert -1
limit_per_search_term = 20
limit_total = -1  # Top N songs. For all results insert -1
offset = 0  # Offset final results by popularity
market = 'US'
# Characters after which the track name does not matter for duplicates
flagged_characters = ['-', '(']
sleep_time_openai = 15  # seconds      #CHANGE THIS

def getGptCompletion(prompt, engine):

    try:
        if 'davinci' in engine:
            completion= openai.Completion.create(engine=engine,
                                                        max_tokens=gpt_max_tokens,
                                                        prompt=prompt)
            choice_response_text = completion['choices'][0].text.strip()
            choice_response_text = completion['choices'][0].text.strip().replace('"', '')
        else:
            completion= openai.ChatCompletion.create(model=engine,
                                                        max_tokens=gpt_max_tokens,
                                                        messages=[{"role": "assistant", "content": prompt}])
                                                        
            choice_response_text = completion['choices'][0]['message']['content'].strip().replace('"', '')
        

        print(f"Sleeping for {str(sleep_time_openai)} seconds")
        time.sleep(sleep_time_openai)

        return choice_response_text


    except Exception as e:
        print("ERROR IN CHATGPT")
        return "No response available. prompt: " + prompt

try:
    from openai_api_song_data.search_youtube import youtube_search
    print("Importing from parent folder")
except:
    from .search_youtube import youtube_search

column_list = ['artist', 'track_name', 'release_year', 'album', 'yt_video_id',
               'model_response', 'popularity', 'duration_ms', 'track_id']
column_name_transform = {'artist': 'Artist', 'track_name': 'Track Name',
                         'release_year': 'Release Year', 'album': 'Album'}
cwd = os.path.dirname(__file__)

# define auth keys
openai.api_key = ""
youtube_api_key = ''

# paths
output_dir = os.path.join(cwd, '..', 'sd_app', 'model_outputs')


def search_spotify_tracks(keyword, sp, target="track", by="track", keyword_id=None):
    search_columns = ['artist', 'track_name', 'release_year',
                      'album', 'popularity', 'duration_ms', 'track_id', 'spotify_url']

    def clean_names_for_list(track_name, keyword):
        '''
            This function cleans the name of the track in order to avoid substrings and names of additional artists.
            Example: "Perfect (Remix) (feat. Doja Cat & BIA)" comes up when searching for "Cat"
            By applying this function, that track would come up as only "Perfect", so it would not appear in the search results
        '''
        start = max(track_name.find('('), track_name.find('-'))
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
    input = urllib.parse.urlencode({'search_query': track_title})
    try:
        html = urllib.request.urlopen(
            "http://www.youtube.com/results?" + input)
        video_id = re.findall(r"watch\?v=(\S{11})", html.read().decode())[0]
    except:
        video_id = ''

    return video_id

def get_youtube_search_results(track_title):

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
                    break
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
    if limit_total != -1:
        df = df.iloc[:limit_total]

    #   Keeping only the relevant columns
    output_df_filtered_w_results = df[column_list]

    output_df_filtered_w_results = output_df_filtered_w_results.rename(
        columns=column_name_transform)
    return output_df_filtered_w_results


def generate_html_file(html):
    output_html_name = f'sample_keywords_output_html_{datetime.now().strftime("%Y%m%d-%H%M%S")}.html'
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
        self.model = data.get('model','gpt-3.5-turbo' )

        self.improve_song = data.get('improve-song', False)
        self.improve_intro = data.get('improve-intro', False)
        self.wordpress =  data.get('wordpress', False)
        
        self.limit = limit_st
        self.offset = offset_res
        self.keys = keys
        
        self.keyword_descriptor=""
        self.by=None

 
    def create_record(self, Search, current_user):
        new_search = Search(
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
            improved_intro=self.improve_intro
        )
        self.search_id = new_search.id

        return new_search

    def run(self, flag_running, stopper):

        try:
            # instantiate spotify api client
            self.sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(client_id=self.keys['sp_user'],client_secret=self.keys['sp_password']),requests_timeout=60)
            resume = self.main_process(stopper)

            flag_running.clear()
            stopper.clear()

            if not resume:
                return "Failed"
            else:
                return "Completed"
        
        except Exception as e:
            flag_running.clear()
            stopper.clear()

            print("Error while running search")
            print(e)

            return "Failed"

    def main_process(self, stopper):

        openai.api_key = self.keys['openai_key']
        youtube_api_key = self.keys['youtube_key']

        def get_openai_yt_data(self, df):
            # Get youtube and openai data
            print(f"Getting Youtube data")
            df_w_spot_and_yt = get_youtube_search_results_for_tracks_dataset(df)

            if not isinstance(df_w_spot_and_yt, pd.DataFrame): return False

            print(f"Getting OpenAI response")
            merged_df_w_results = get_openai_model_responses(self, df_w_spot_and_yt)
            
            if not isinstance(merged_df_w_results, pd.DataFrame): return False


            return merged_df_w_results
        
        def get_youtube_search_results_for_tracks_dataset(df_w_spot_df):

            track_id_name_and_yt_url = []

            for track_id, track_name, artist in list(zip(df_w_spot_df['track_id'],
                                                        df_w_spot_df['track_name'],
                                                        df_w_spot_df['artist']
                                                        )):
                if (stopper.is_set()):
                    print("Stopped search")
                    return False
                
                yt_video_id = get_youtube_search_results(track_name + ' ' + artist)
                track_id_name_and_yt_url.append((track_id, track_name, yt_video_id))

            # Convert to dataframe
            track_id_w_yt_data_df = pd.DataFrame(track_id_name_and_yt_url,
                                                columns=['track_id', 'track_name', 'yt_video_id'])
            track_id_w_yt_data_df.drop(columns=['track_name'], inplace=True)

            # Merge with spotify data
            tracks_df_with_yt = pd.merge(df_w_spot_df, track_id_w_yt_data_df, on='track_id', how='right')
            # Drop duplicate tracks
            tracks_df_with_yt = tracks_df_with_yt.drop_duplicates(subset=['track_id'])

            return tracks_df_with_yt

        def get_openai_model_responses(self, df_w_spot_and_yt):
            tracks_data_w_completion_text = []


            for i, track in df_w_spot_and_yt.iterrows():
                if (stopper.is_set()):
                    print("Stopped search")
                    return False
                
                
                values_to_replace = {
                    '[track name]':track.track_name,
                    '[artist]':track.artist,
                    '[release year]': track.release_year
                } | self.values_to_replace

                # here is the prompt
                if self.prompt == '':
                    prompt = f'Write a simple text presenting the song {track.track_name} by {track.artist} from {track.release_year} ' \
                            f'describing how it sounds, the feeling of the song, and its meaning. The text should be at least 70 words but no longer than 100 words written in easy-to-understand language.  ' \
                            f'Keep the sentences short and the paragraphs should be no longer than 3 sentences long. Do not use any quotation marks in the text.'
                else:
                    prompt = self.prompt.lower()
                    for placeholder, value in values_to_replace.items():
                        prompt = prompt.replace(placeholder, value)
                    prompt = prompt.capitalize()

                print("||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||")
                print(f'The prompt is: {prompt}')
                #completion
                choice_response_text = getGptCompletion(prompt, self.model)

                if self.improve_song: 
                    print("Improving response...")
                    choice_response_text = improve_gpt_response(choice_response_text)

                tracks_data_w_completion_text.append((track.track_id, choice_response_text))

                print("Final response text: " + choice_response_text)
            
            model_res_df = pd.DataFrame(tracks_data_w_completion_text, columns=['track_id', 'model_response'])

            merged_df_w_results = pd.merge(df_w_spot_and_yt, model_res_df, on='track_id')
            merged_df_w_results = merged_df_w_results.drop_duplicates(subset=['track_id'])

            return merged_df_w_results

        def get_openai_intro(self):

            print("Getting OpenAI introduction")
            print("prompt: " + self.intro_prompt)

            choice_response_text = getGptCompletion(self.intro_prompt, self.model)
            
            if self.improve_intro: 
                choice_response_text = improve_gpt_response(choice_response_text)


            return choice_response_text

        def improve_gpt_response(old_text):
            print("Improving openAI response.")

            if '[old text]' in self.improver_prompt:
                prompt = self.improver_prompt.replace('[old text]', old_text)
            else:
                prompt = self.improver_prompt + '\n\n' + old_text

            return getGptCompletion(prompt, 'gpt-3.5-turbo')
        
        
        raw_output_dfs = []
        output_dfs = []

        output_df = self.get_search_results(stopper)
        if not isinstance(output_df, pd.DataFrame): return False

        #   Get yt and openai data
        output_df_data = get_openai_yt_data(self, output_df)
        if not isinstance(output_df_data, pd.DataFrame): return False

        #   Clean and sort results
        clean_sorted_data = clean_and_sort(output_df_data)
        n_songs=clean_sorted_data.shape[0]

        if self.by=="artist":
            slug = self.artist_name.replace(" ", "-").lower() + "-songs"
            wp_title = f'{n_songs} Best {self.artist_name.title()} Songs'

        elif self.by=="keyword":
            slug = 'songs-about-' + self.keyword.lower()
            wp_title = f'{str(n_songs)} Songs About {self.keyword.title()}'

        intro = get_openai_intro(self)
        html = generate_html(clean_sorted_data, intro)
        if self.wordpress: create_wp_draft(wp_title, html, slug, self.keys)

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
        self.values_to_replace = {'[keyword]': self.keyword}

    
    def get_search_results(self, stopper):
        search_term_dfs = []  # list with search term results

        for keyword in self.sp_keywords:

            if (stopper.is_set()):
                print("Stopped search")
                return False
            
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
        
        self.keyword_descriptor=self.artist_name
        self.values_to_replace = {'artist':self.artist_name}
    
    def get_search_results(self, stopper):

        if (stopper.is_set()):
            print("Stopped search")
            return False

        print("|||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||")
        print(f"Searching for top songs by {self.artist_name}")
        df_w_spot_df = search_spotify_tracks(self.artist_name, self.sp, target="track", by="artist", keyword_id=self.artist_id)

        df_w_spot_df.sort_values('popularity', ascending=False, inplace=True)
        print("Limiting search results to " + str(self.limit))

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

    
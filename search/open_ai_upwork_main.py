
import argparse
import json
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

limit_per_keyword=-1     #Top N songs per keyowrd (ex. cat). For all results insert -1
limit_per_search_term=20    #Top N songs for search term (ex. animals). For all results insert -1
limit_total=-1  #Top N songs. For all results insert -1
market='US'
flagged_characters = ['-', '('] #Characters after which the track name does not matter for duplicates 
sleep_time_openai=15 #seconds      #CHANGE THIS

try:
    from openai_api_song_data.search_youtube import youtube_search
    print("Importing from parent folder")
except:
    from .search_youtube import youtube_search

column_list = ['keyword', 'specific_keyword', 'artist', 'track_name', 'release_year', 'album', 'yt_video_id',
                        'model_response', 'popularity', 'duration_ms', 'track_id']
column_name_transform = {'artist': 'Artist','track_name': 'Track Name','release_year': 'Release Year','album': 'Album'}
cwd = os.getcwd()

# define auth keys
openai.api_key = ""
youtube_api_key = ''

# paths
output_dir = f'{cwd}/song_search/sd_app/model_outputs'

def get_input_keyword_data(input_keyword_csv_filepath):
    input_kw_df = pd.read_csv(input_keyword_csv_filepath, names=['index','search_term', 'keyword'])
    return input_kw_df

def search_spotify_tracks(keyword):
    search_columns=['artist', 'track_name', 'release_year', 'album', 'popularity', 'duration_ms', 'track_id', 'spotify_url']
    def clean_names_for_list(track_name, keyword):   
        '''
            This function cleans the name of the track in order to avoid substrings and names of additional artists.
            Example: "Perfect (Remix) (feat. Doja Cat & BIA)" comes up when searching for "Cat"
        '''
        start = max(track_name.find('('),track_name.find('-'))
        if start != -1:
            track_name = track_name[:start]

        n_words_kw = len(keyword.split(' '))
        track_name_wlist = track_name.lower().split(' ')
        
        if n_words_kw <= 1:
            return track_name_wlist

        else:
            n_words_tn = len(track_name_wlist)
            track_name_wlist = track_name.lower().split(' ')
            word_combinations = [' '.join(track_name_wlist[i:i+n_words_kw]) for i in range(0,n_words_tn-1)]
            return word_combinations

    # instantiate spotify api client
    sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(client_id='0e73b1eb155746f8bcccbde4b6e02bf6',
                                                               client_secret='c60a606e52314055b2e28d12722311fc'))
    
    search_results_clean = []
    total_results = sp.search(q=f'track:{keyword}', type="track", limit=1, offset=0)['tracks']['total']

    if total_results == 0: return pd.DataFrame(columns=search_columns)     #Avoid processing if there are no results

    for offset in range(0,total_results-1,50):
        if offset >=1000:   #Maximum offset spotipy can handle
            break
        
        track_search_results = sp.search(q=f'track:{keyword}', type="track", limit=50, offset=offset, market=market)['tracks']['items']
        track_search_results_clean = [track for track in track_search_results if keyword in clean_names_for_list(track.get('name', None), keyword)]
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
         
    df_search_results_clean = pd.DataFrame(search_results_clean, columns=search_columns)
    return df_search_results_clean

def scrape_youtube_search_results(track_title):
    input = urllib.parse.urlencode({'search_query': track_title})
    try:
        html = urllib.request.urlopen("http://www.youtube.com/results?" + input)
        video_id = re.findall(r"watch\?v=(\S{11})", html.read().decode())[0]
    except:
        video_id=''
    
    return video_id

def get_youtube_search_results(track_title):
    
    options = argparse.Namespace(q=track_title, max_results=1)
    try:
        #Try getting the video data from google API
        search_results = youtube_search(options, youtube_api_key)
        video_id = search_results['items'][0]['id']['videoId']
    except HttpError as error:
        # check if the error is due to exceeding the daily quota
        if error.resp.status in [403, 404]:
            # handle the error and switch to scraping solution
            print('Daily quota for YouTube Data API exceeded... Switching to YouTube scraping solution...')
            video_id = scrape_youtube_search_results(track_title)
        else:
            video_id = ''
    except Exception as e:
        print('There was an error using the YouTube Data API... Switching to YouTube scraping solution...')
        video_id = scrape_youtube_search_results(track_title)
        
 #   video_url = f'https://www.youtube.com/watch?v={video_id}'
    return video_id

def get_youtube_search_results_for_tracks_dataset(df_w_spot_df):
    
    track_id_name_and_yt_url = []

    for track_id, track_name, artist in list(zip(df_w_spot_df['track_id'],
                                                 df_w_spot_df['track_name'],
                                                 df_w_spot_df['artist']
                                                 )):
        yt_video_id = get_youtube_search_results(track_name + ' ' + artist)
        track_id_name_and_yt_url.append((track_id, track_name, yt_video_id))

    track_id_w_yt_data_df = pd.DataFrame(track_id_name_and_yt_url,
                                         columns=['track_id', 'track_name', 'yt_video_id'])
    track_id_w_yt_data_df.drop(columns=['track_name'], inplace=True)
    tracks_df_with_yt = pd.merge(df_w_spot_df, track_id_w_yt_data_df, on='track_id', how='right')
    tracks_df_with_yt = tracks_df_with_yt.drop_duplicates(subset=['track_id', 'keyword'])

    return tracks_df_with_yt
 
def get_openai_model_responses(df_w_spot_and_yt):
    name_artist_year_tuples = list(df_w_spot_and_yt[["track_id",
                                                           "track_name",
                                                           "artist",
                                                           "release_year"]].itertuples(index=False,
                                                                                       name=None))
    completions = []
    tracks_data_w_completion_text = []
    for track_id, track_name, artist, release_year in name_artist_year_tuples:
        # here is the prompt
        prompt = f'Write a simple text presenting the song {track_name} by {artist} from {release_year} ' \
                 f'describing how it sounds, the feeling of the song, and its meaning. The text should be at least 70 words but no longer than 100 words written in easy-to-understand language. Do not use any quotation marks in the text.'
        # CHANGE THIS
        completion = openai.Completion.create(engine="text-davinci-003",
                                              max_tokens=150,
                                              prompt=prompt)
        
        choice_response_text = completion['choices'][0].text.strip()
        print("||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||")
        print(f'The prompt is: {prompt}')
        choice_response_text = completion['choices'][0].text.strip().replace('"', '')
        completions.append(completion)
        tracks_data_w_completion_text.append((track_id, prompt, choice_response_text))
        time.sleep(sleep_time_openai)
        print(f"Sleeping for {str(sleep_time_openai)} seconds")
    model_res_df = pd.DataFrame(tracks_data_w_completion_text, columns=['track_id', 'prompt', 'model_response'])

    merged_df_w_results = pd.merge(df_w_spot_and_yt, model_res_df, on='track_id')
    merged_df_w_results = merged_df_w_results.drop_duplicates(subset=['track_id', 'keyword'])
    return merged_df_w_results

def cleanse_track_duplicates(df):
    def delete_after_character(track_name):
        for c in flagged_characters:
            end = track_name.find(c)
            if end != -1:
                track_name = track_name[:end-1]
                break
        return track_name
    
    #Use clean track names
    df['track_name_clean'] = df.apply(lambda x: delete_after_character(x['track_name']), axis=1)

    df.drop_duplicates(subset='track_name_clean', keep='first', inplace=True)
    print(df[['track_name', 'popularity', 'specific_keyword']])
    return df

def main_proc(input_data):

    keyword_df = input_data

    output_df_not_filtered = []
    output_dfs = []
    #search_term-level loop
    for search_term in keyword_df['search_term'].unique():
        search_term_dfs = []    #list with search term results

        #keyword-level loop
        for keyword in keyword_df[keyword_df.search_term == search_term]['keyword'].unique():
            print(f"|||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||")
            print(f"Starting first keyword: {keyword}")
            print(f'Getting most popular songs containing our {keyword}')
            df_w_spot_df = search_spotify_tracks(keyword)
            if df_w_spot_df.shape[0] == 0:
                df_w_spot_df['specific_keyword'] = keyword
                search_term_dfs.append(df_w_spot_df)
                continue
            df_w_spot_df.sort_values('popularity', ascending=False, inplace=True)  
            if limit_per_keyword != -1: df_w_spot_df = df_w_spot_df.iloc[:limit_per_keyword+1]  #keyword-level filtering
            
            df_w_spot_df['specific_keyword'] = keyword    #For traceability purposes
            search_term_dfs.append(df_w_spot_df)

        st_out_sp_df = pd.concat(search_term_dfs)      #search term-level dataframe
        if st_out_sp_df.shape[0] == 0:
            st_out_sp_df['keyword'] = search_term
            output_df_not_filtered.append(st_out_sp_df)
            continue
        st_out_sp_df.sort_values('popularity', ascending=False, inplace=True)
        
        #drop duplicates
        out_df_no_duplicates = cleanse_track_duplicates(st_out_sp_df)
        if limit_per_search_term != -1: out_df_no_duplicates = out_df_no_duplicates.iloc[:limit_per_search_term]       #search_term-level filtering

        print("Prepping our KW output...")
        # prep for final output
        out_df = out_df_no_duplicates.copy()
        out_df['keyword'] = search_term
        
        output_df_not_filtered.append(out_df)

    output_df_filtered = pd.concat(output_df_not_filtered)

    #Filter most popular songs (total)
    output_df_filtered.sort_values('popularity', ascending=False, inplace=True)
    if limit_total != -1: output_df_filtered = output_df_filtered.iloc[:limit_total]
    
    #Get youtube and openai data
    print(f"Getting Youtube data")
    df_w_spot_and_yt = get_youtube_search_results_for_tracks_dataset(output_df_filtered)
    print(f"Getting OpenAI response")
    try:
        merged_df_w_results = get_openai_model_responses(df_w_spot_and_yt)
    except:
        merged_df_w_results = df_w_spot_and_yt.copy()
        merged_df_w_results['model_response'] = ''
    
    output_df_filtered_w_results = merged_df_w_results[column_list]
    
    output_df_filtered_w_results = output_df_filtered_w_results.rename(columns=column_name_transform)


    #Loop again for consolidating csv file
    for search_term in keyword_df['search_term'].unique():
        out_df_keep_2 = output_df_filtered_w_results[output_df_filtered_w_results.keyword == search_term]
        out_df_keep_2['song_key_index'] = [f'Song {i + 1}' for i in range(len(out_df_keep_2))]
        out_df_keep_3 = out_df_keep_2.set_index('song_key_index')
        output_dict = out_df_keep_3.to_dict(orient='index')

        # Use json.dumps() to convert the dictionary to a JSON string,
        json_string = json.dumps(output_dict, ensure_ascii=False)

        # Use json.loads() to parse the JSON string,
        # then use json.dumps() to re-serialize the parsed JSON data,
        # setting the ensure_ascii parameter to False
        json_string = json.dumps(json.loads(json_string), ensure_ascii=False)
        
        slug = 'songs-about-' + search_term

        output_data = {'id': str(uuid4()),
                        'track_name_keyword': search_term,
                        'H1': f'{len(out_df_keep_3)} Songs with {search_term.capitalize()} in the title',
                        'slug': slug,
                        'intro': '',
                        'number_of_songs_listed': len(out_df_keep_3),
                        'json': json_string}

        output_df = pd.DataFrame([output_data])
        print(f"A sample of the final output dataframe for {search_term}")
        print(output_df.head())

        output_dfs.append(output_df)

    print("Combining all keyword results into one output...")
    final_output_df = pd.concat(output_dfs)

    print(f'There are {len(final_output_df)} records in the output CSV...')

    output_fname = f'sample_keywords_output_{datetime.now().strftime("%Y%m%d-%H%M%S")}.csv'

    print(f"Saving CSV file to : {os.path.join(output_dir, output_fname)}")

    final_output_df.to_csv(os.path.join(output_dir, output_fname), sep=';', index=False)
    return output_fname

'''
if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--input-fp', help='Full filepath to the input CSV')
    # parser.add_argument('--output-fp', help='Full filepath to the output CSV')
    args = parser.parse_args()

    print(args)

    main_proc(args)
    #except Exception as e:
    #    print(f'An error {e} occurred:')
'''

def search(input_data, limit_st, limit_tot, keys):
    global limit_per_search_term, limit_total, youtube_api_key

    openai.api_key = keys['openai_key']
    youtube_api_key = keys['youtube_key']

    limit_total = limit_tot
    limit_per_search_term = limit_st
    return main_proc(input_data)

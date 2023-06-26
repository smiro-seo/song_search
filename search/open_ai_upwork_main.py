
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
        

    return completion, choice_response_text

try:
    from openai_api_song_data.search_youtube import youtube_search
    print("Importing from parent folder")
except:
    from .search_youtube import youtube_search

column_list = ['keyword', 'specific_keyword', 'artist', 'track_name', 'release_year', 'album', 'yt_video_id',
               'model_response', 'popularity', 'duration_ms', 'track_id']
column_name_transform = {'artist': 'Artist', 'track_name': 'Track Name',
                         'release_year': 'Release Year', 'album': 'Album'}
cwd = os.path.dirname(__file__)

# define auth keys
openai.api_key = ""
youtube_api_key = ''

# paths
output_dir = os.path.join(cwd, '..', 'sd_app', 'model_outputs')


def get_input_keyword_data(input_keyword_csv_filepath):
    input_kw_df = pd.read_csv(input_keyword_csv_filepath, names=[
                              'index', 'search_term', 'keyword'])
    return input_kw_df


def search_spotify_tracks(keyword, keys, target="track", by="track", keyword_id=None):
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

    # instantiate spotify api client
    sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(client_id=keys['sp_user'],
                                                               client_secret=keys['sp_password']))

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
        print(df[['track_name', 'popularity', 'specific_keyword']])
        return df


def get_search_results(keyword_df, search_term, stopper, keys):

    search_term_dfs = []  # list with search term results

    #   keyword-level loop (e.g. horse)
    for keyword in keyword_df['keyword'].unique():

        if (stopper.is_set()):
            print("Stopped search")
            return False
        print(
            f"|||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||")
        print(f"Starting first keyword: {keyword}")
        print(f'Getting most popular songs containing our {keyword}')
        df_w_spot_df = search_spotify_tracks(keyword, keys)
        if df_w_spot_df.shape[0] == 0:
            df_w_spot_df['specific_keyword'] = keyword
            search_term_dfs.append(df_w_spot_df)
            continue
        df_w_spot_df.sort_values('popularity', ascending=False, inplace=True)
        if limit_per_keyword != -1:
            # keyword-level filtering
            df_w_spot_df = df_w_spot_df.iloc[:limit_per_keyword+1]

        # For traceability purposes
        df_w_spot_df['specific_keyword'] = keyword
        search_term_dfs.append(df_w_spot_df)

    # search term-level dataframe
    st_out_sp_df = pd.concat(search_term_dfs)
    if st_out_sp_df.shape[0] == 0:
        st_out_sp_df['keyword'] = search_term
        return st_out_sp_df

    st_out_sp_df.sort_values('popularity', ascending=False, inplace=True)

    # drop duplicates
    out_df_no_duplicates = cleanse_track_duplicates(st_out_sp_df)
    if limit_per_search_term != -1:
        if out_df_no_duplicates.shape[0] > offset + limit_per_search_term:
            # search_term-level filtering
            out_df_no_duplicates = out_df_no_duplicates.iloc[offset:offset +
                                                             limit_per_search_term]
        elif out_df_no_duplicates.shape[0] > offset:
            out_df_no_duplicates = out_df_no_duplicates.iloc[offset:]
        else:
            print(f"Offset too big for results. Returning empty table.")
            out_df_no_duplicates = pd.DataFrame(
                columns=out_df_no_duplicates.columns)

    print("Prepping our KW output...")
    # prep for final output
    out_df = out_df_no_duplicates.copy()
    out_df['keyword'] = search_term

    return out_df

def get_search_results_by_artist(artist, stopper, artist_id, keys):

    if (stopper.is_set()):
        print("Stopped search")
        return False
    print(
        f"|||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||")
    print(f"Searching for top songs by {artist}")
    df_w_spot_df = search_spotify_tracks(artist, keys, target="track", by="artist", keyword_id=artist_id)

    df_w_spot_df.sort_values('popularity', ascending=False, inplace=True)
    print("Limiting search results to " + str(limit_per_search_term))
    if limit_per_search_term != -1:
        if df_w_spot_df.shape[0] > offset + limit_per_search_term:
            # search_term-level filtering
            df_w_spot_df = df_w_spot_df.iloc[offset:offset + limit_per_search_term]
        elif df_w_spot_df.shape[0] > offset:
            df_w_spot_df = df_w_spot_df.iloc[offset:]
        else:
            print(f"Offset too big for results. Returning empty table.")
            df_w_spot_df = pd.DataFrame(columns=df_w_spot_df.columns)

    # For traceability purposes
    df_w_spot_df['keyword'] = artist
    df_w_spot_df['specific_keyword'] = artist

    print("Prepping our KW output...")
    # prep for final output

    return df_w_spot_df



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


def get_json_string(search_term_df):

    #search_term_df.assign(song_key_index=lambda x: f'Song {x.index + 1}')
    search_term_df['song_key_index'] = [f'Song {i + 1}' for i in range(len(search_term_df))]
    out_df_keep = search_term_df.set_index('song_key_index')
    output_dict = out_df_keep.to_dict(orient='index')

    # Use json.dumps() to convert the dictionary to a JSON string,
    json_string = json.dumps(output_dict, ensure_ascii=False)

    # Use json.loads() to parse the JSON string,
    # then use json.dumps() to re-serialize the parsed JSON data,
    # setting the ensure_ascii parameter to False
    json_string = json.dumps(json.loads(
        json_string), ensure_ascii=False)

    return json_string, len(out_df_keep)


def generate_csv(df):
    print("Combining all keyword results into one output...")
    print(f'There are {len(df)} records in the output CSV...')

    output_fname = f'sample_keywords_output_{datetime.now().strftime("%Y%m%d-%H%M%S")}.csv'
    output_path = os.path.join(output_dir, output_fname)

    print(f"Saving CSV file to : {output_path}")

    if not os.path.exists(output_dir):
        os.mkdir(output_dir)
    df.to_csv(output_path, sep=';', index=False)

    return output_fname

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


def main_proc(input_data, stopper, keys, wordpress,by_artist):

    def get_openai_yt_data(df, prompt, improver_prompt, improve):
        # Get youtube and openai data
        print(f"Getting Youtube data")
        df_w_spot_and_yt = get_youtube_search_results_for_tracks_dataset(df)
        print(f"Getting OpenAI response")
        try:
            merged_df_w_results = get_openai_model_responses(df_w_spot_and_yt, prompt, improver_prompt, improve, by_artist=by_artist)
        except Exception as e:
            print("There was an error recovering model response.")
            print(e)
            merged_df_w_results = df_w_spot_and_yt.copy()
            merged_df_w_results['model_response'] = ''

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

        track_id_w_yt_data_df = pd.DataFrame(track_id_name_and_yt_url,
                                            columns=['track_id', 'track_name', 'yt_video_id'])
        track_id_w_yt_data_df.drop(columns=['track_name'], inplace=True)
        tracks_df_with_yt = pd.merge(
            df_w_spot_df, track_id_w_yt_data_df, on='track_id', how='right')
        tracks_df_with_yt = tracks_df_with_yt.drop_duplicates(
            subset=['track_id', 'keyword'])

        return tracks_df_with_yt

    def get_openai_model_responses(df_w_spot_and_yt, original_prompt, improver_prompt, improve=False, by_artist=False):
        
        name_artist_year_tuples = list(df_w_spot_and_yt[["track_id",
                                                        "track_name",
                                                        "artist",
                                                        "release_year",
                                                        'keyword']].itertuples(index=False,
                                                                                    name=None))
        completions = []
        tracks_data_w_completion_text = []


        for track_id, track_name, artist, release_year, keyword in name_artist_year_tuples:
            #   Placeholders to replace in prompt
            values_to_replace = {
                '[track name]':track_name,
                '[artist]':artist,
                '[release year]': release_year,
                '[keyword]': keyword
            }

            if (stopper.is_set()):
                print("Stopped search")
                return False

            # here is the prompt
            if original_prompt == '':
                prompt = f'Write a simple text presenting the song {track_name} by {artist} from {release_year} ' \
                        f'describing how it sounds, the feeling of the song, and its meaning. The text should be at least 70 words but no longer than 100 words written in easy-to-understand language.  ' \
                        f'Keep the sentences short and the paragraphs should be no longer than 3 sentences long. Do not use any quotation marks in the text.'
            else:
                prompt = original_prompt.lower()
                for placeholder, value in values_to_replace.items():
                    prompt = prompt.replace(placeholder, value)
                prompt = prompt.capitalize()

            print("||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||")
            print(f'The prompt is: {prompt}')
            #completion
            completion, choice_response_text = getGptCompletion(prompt, input_data['model'])
                          
            print(f"Sleeping for {str(sleep_time_openai)} seconds")
            time.sleep(sleep_time_openai)
            print("Improving response...")

            if improve: 
                completion, choice_response_text = improve_gpt_response(choice_response_text, improver_prompt)

            completions.append(completion)
            tracks_data_w_completion_text.append(
                (track_id, prompt, choice_response_text))
            time.sleep(sleep_time_openai)
            print(f"Sleeping for {str(sleep_time_openai)} seconds")

            print("Final response text: " + choice_response_text)
        model_res_df = pd.DataFrame(tracks_data_w_completion_text, columns=[
                                    'track_id', 'prompt', 'model_response'])

        merged_df_w_results = pd.merge(
            df_w_spot_and_yt, model_res_df, on='track_id')
        if not by_artist: merged_df_w_results = merged_df_w_results.drop_duplicates(subset=['track_id', 'keyword'])

        return merged_df_w_results

    def get_openai_intro(prompt, keyword,improver_prompt, improve):

        print("Getting OpenAI introduction")

        prompt = prompt.replace('[keyword]', keyword).replace('[artist]', keyword)
        print("prompt: " + prompt)

        try:
            completion, choice_response_text = getGptCompletion(prompt, input_data['model'])
            
            if improve: 
                n, choice_response_text = improve_gpt_response(choice_response_text,improver_prompt)
        except:
            choice_response_text="long text with words " * 50


        return choice_response_text

    def improve_gpt_response(choice_response_text, improver_prompt):
        print("Improving openAI response.")

        prompt = improver_prompt + '\n' + choice_response_text
        print("New prompt: " + prompt)
        
        return getGptCompletion(prompt, 'gpt-3.5-turbo')
    
    
    raw_output_dfs = []
    output_dfs = []

    if by_artist:
        output_df = get_search_results_by_artist(input_data['name'], stopper, input_data['id'], keys)  
        print("output search: ")
    
    else:
        #   search_term-level loop (e.g. animals)
        keyword_df = input_data['keywords']
        for search_term in keyword_df['search_term'].unique():
            search_term_df = get_search_results(
                keyword_df[keyword_df['search_term'] == search_term], search_term, stopper, keys)
            raw_output_dfs.append(search_term_df)

        #   This contains only the truncated list (depending on limit imposed) of songs with basic metadata obtained from spotify
        output_df = pd.concat(raw_output_dfs)

    #   Get yt and openai data
    output_df_data = get_openai_yt_data(output_df, input_data['prompt'], input_data['improver-prompt'], input_data['improve-song'])

    #   Clean and sort results
    clean_sorted_data = clean_and_sort(output_df_data)
    print("clean data:")
    print(clean_sorted_data)

    if(by_artist):
        # Loop again for consolidating csv file
        json_string, n_songs = get_json_string(clean_sorted_data)
        slug = input_data['name'].replace(" ", "-").lower() + "-songs"

        output_data = {'id': str(uuid4()),
                    'track_name_keyword': input_data['name'],
                    'H1': f'{n_songs} Best {input_data["name"].title()} Songs',
                    'slug': slug,
                    'intro': '',
                    'number_of_songs_listed': n_songs,
                    'json': json_string}

        output_df = pd.DataFrame([output_data])
        intro = get_openai_intro(input_data['intro-prompt'], input_data['name'], input_data['improver-prompt'], input_data['improve-intro'])

        html = generate_html(json_string, intro)

        wp_title = output_data['H1']
        if wordpress: create_wp_draft(wp_title, html, slug, keys)

        output_dfs.append(output_df)

    else:

        # Loop again for consolidating csv file
        for search_term in keyword_df['search_term'].unique():

            json_string, n_songs = get_json_string(
                clean_sorted_data[clean_sorted_data.keyword == search_term])
            slug = 'songs-about-' + search_term

            output_data = {'id': str(uuid4()),
                        'track_name_keyword': search_term,
                        'H1': f'{n_songs} Songs with {search_term.capitalize()} in the title',
                        'slug': slug,
                        'intro': '',
                        'number_of_songs_listed': n_songs,
                        'json': json_string}

            output_df = pd.DataFrame([output_data])
            intro = get_openai_intro(input_data['intro-prompt'], search_term, input_data['improver-prompt'], input_data['improve-intro'])

            html = generate_html(json_string, intro)

            wp_title = str(n_songs) + ' ' + slug.replace('-', ' ').title()
            if wordpress: create_wp_draft(wp_title, html, slug, keys)

            output_dfs.append(output_df)

    #   output_csv_name = generate_csv(pd.concat(output_dfs))
    output_html_name = generate_html_file(html)

    return True



def search(input_data, limit_st, offset_res, keys, stopper, wordpress,by_artist):
    global limit_per_search_term, limit_total, youtube_api_key, offset

    openai.api_key = keys['openai_key']
    youtube_api_key = keys['youtube_key']

    offset = offset_res
    limit_total = -1
    limit_per_search_term = limit_st
    return main_proc(input_data, stopper, keys, wordpress,by_artist)


def search_artists(artist_name, keys):

    artists = search_spotify_tracks(artist_name,keys, target="artist")
    artists.sort_values('popularity', ascending=False, inplace=True)
    return artists

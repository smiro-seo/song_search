#!/usr/bin/python

# This sample executes a search request for the specified search term.
# Sample usage:
#   python search.py --q=surfing --max-results=10
# NOTE: To use the sample, you must provide a developer key obtained
#       in the Google APIs Console. Search for "REPLACE_ME" in this code
#       to find the correct place to provide that key..

import argparse

import urllib.request
import urllib.parse
import re

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

YOUTUBE_API_SERVICE_NAME = 'youtube'
YOUTUBE_API_VERSION = 'v3'


def youtube_search(options, DEVELOPER_KEY):
    youtube = build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION,
                    developerKey=DEVELOPER_KEY)

    # Call the search.list method to retrieve results matching the specified
    # query term.
    search_response = youtube.search().list(
        q=options.q,
        part='id,snippet',
        maxResults=options.max_results
    ).execute()

    # videos = []
    # channels = []
    # playlists = []
    # 
    # # Add each result to the appropriate list, and then display the lists of
    # # matching videos, channels, and playlists.
    # for search_result in search_response.get('items', []):
    #     if search_result['id']['kind'] == 'youtube#video':
    #         videos.append('%s (%s)' % (search_result['snippet']['title'],
    #                                    search_result['id']['videoId']))
    #     elif search_result['id']['kind'] == 'youtube#channel':
    #         channels.append('%s (%s)' % (search_result['snippet']['title'],
    #                                      search_result['id']['channelId']))
    #     elif search_result['id']['kind'] == 'youtube#playlist':
    #         playlists.append('%s (%s)' % (search_result['snippet']['title'],
    #                                       search_result['id']['playlistId']))
    # 
    # print('Videos:\n', '\n'.join(videos), '\n')
    # print('Channels:\n', '\n'.join(channels), '\n')
    # print('Playlists:\n', '\n'.join(playlists), '\n')
    return search_response


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
                print("OK")
                break
    except Exception as e:
        print("ERROR")
        print(e)
        video_id = ''
        
    return video_id



if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--q', help='Search term', default='Google')
    parser.add_argument('--max-results', help='Max results', default=1)
    args = parser.parse_args()
    
    print(args)

    try:
        youtube_search(args)
    except HttpError as e:
        print('An HTTP error %d occurred:\n%s' % (e.resp.status, e.content))

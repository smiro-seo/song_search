from .open_ai_upwork_main import Search_Keyword, search_artists, Search_Artist , Search_Spotify_Keyword, Search_Spotify_Artist

def search_artist(artist_name, keys):
    return search_artists(artist_name=artist_name, keys=keys)

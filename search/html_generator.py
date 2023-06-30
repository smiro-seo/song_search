import json
from airium import Airium

spotify_img = '<img class="gb-image gb-image-1d75b3e9" \
    src="https://songpier.com/wp-content/uploads/2022/05/listen-spotify-button-edited-e1671691367203.png" \
    alt="spotify", title="listen-spotify-button" />'


def generate_html(data, intro, return_full_text=False):

    print("Generating HTML")
    full_text = intro

    a = Airium()

    #   Intro
    a.p(_t=intro)

    # Generate HTML file
    for i, song_data in data.iterrows():
        full_text += '\n' + song_data["model_response"]
        title = f"{song_data['Track Name']} &#8211; {song_data['Artist'].title()}"    

        #   Title
        with a.h2(klass="wp-block-heading"):
            a(
                f"{str(i+1)}. {title}"
            )

        #   Video
        if song_data["yt_video_id"]!= "":
            with a.div(klass="wp-block-embed__wrapper"):
                with a.div(f'data-id="{song_data["yt_video_id"]}" data-src="https://www.youtube.com/embed/{song_data["yt_video_id"]}" data-query="feature=oembed"', klass="rll-youtube-player"):
                    #with a.noscript():
                    a.iframe("allowfullscreen", title=title, width="840", height="473", 
                    src=f"https://www.youtube.com/embed/{song_data['yt_video_id']}?feature=oembed", frameborder="0", 
                    allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture")

        #   Song Data
        with a.div(klass="songfacts"):
            for item in ["Artist", "Track Name", "Album", "Release Year"]:
                a(f"<strong>{item}: </strong>{song_data[item]}")
        
        #   Spotify
        with a.div(klass="spotify"):
            a.a(klass="spotify", href=f"https://open.spotify.com/track/{song_data['track_id']}",
            target="_blank", rel="noopener", _t=spotify_img)

        #   Description
        a.p(_t=song_data["model_response"])
    

    # Casting the file to a string to extract the value
    html = str(a)

    if return_full_text: return html, full_text
    else: return html


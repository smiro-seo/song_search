import json
from airium import Airium
import os

cwd = os.path.dirname(__file__)

with open(os.path.join(cwd,'youtube_api_script.txt'), 'r') as f:
    script_string = f.read()

def generate_html(json_string):

    print("Generating HTML")
    data = json.loads(json_string)
    # print([val.specific_keyword for key, val in data.items()])

    a = Airium()
    
    # Generate HTML file
    for song, song_data in data.items():
        title = f"{song_data['Track Name']} &#8211&#32;{song_data['Artist'].title()}"    
        #   song_data["model_response"] = "Nice song!!"

        #   Title
        with a.h2(klass="wp-block-heading"):
            a(
                f"{song.split(' ')[1]}. {title}"
            )

        #   Video
        if song_data["yt_video_id"]!= "":
            with a.figure(klass="wp-block-embed is-type-video is-provider-youtube wp-block-embed-youtube wp-embed-aspect-16-9 wp-has-aspect-ratio"):
                with a.div(klass="wp-block-embed__wrapper"):
                    with a.div(f'data-id="{song_data["yt_video_id"]}" data-src="https://www.youtube.com/embed/{song_data["yt_video_id"]}" data-query="feature=oembed"', klass="rll-youtube-player"):
                        #with a.noscript():
                        a.iframe("allowfullscreen", title=title, width="840", height="473", src=f"https://www.youtube.com/embed/{song_data['yt_video_id']}?feature=oembed", frameborder="0", allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture")

        #   Song Data
        with a.div(klass="songfacts"):
            for item in ["Artist", "Track Name", "Album", "Release Year"]:
                a.strong(_t=item + ": ")
                a(song_data[item])
                a.br()

            #   Spotify
            with a.a(klass="spotify", href=f"https://open.spotify.com/track/{song_data['track_id']}", target="_blank", rel="noopener" ):
                a.img('src="https://songpier.com/wp-content/uploads/2022/05/listen-spotify-button-edited-e1671691367203.png"',
                width="292", height="73", klass="gb-image gb-image-1d75b3e9", 
                alt="spotify", title="listen-spotify-button")

        #   Description
        a.p(_t=song_data["model_response"])
    
    #a(script_string)

    # Casting the file to a string to extract the value
    html = str(a)
    print(html)

    return html


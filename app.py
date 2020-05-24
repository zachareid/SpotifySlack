from flask import request
from flask import Flask
import requests
import re

import spotipy

app = Flask(__name__)

token = "UYXuhkMMui7Vhk4APkQ7poaL"
spotify_reg = "[^\/][\w]+(?=\?)"
playlist_id = "2yjszF9EexqHgURRJ5GTSI"
oauth_token = "BQD2bTiwfISkBZulVOFiO-nuhazXI4oSkO2R3xR88StipvAAq2vMcK3RfGgJIIp6LLI8nERPwyOUeChXbqp_3FaTL_4TJUFObkRaB2gymBw8f7S081jM5_Zxz4jUqOaVRPVUvsngo1fHOEcuO0KDZ7P4z74FskKDkClBrbWYsYwqFmxrbLJ20gLmIvqsTkVib1Q"
username = "bdejun1gahnpit25tfaibrmun"



@app.route('/')
def hello_world():
    return 'Hello, World!'

@app.route('/new_message2', methods=['GET', 'POST'])
def new_message(): 
    print("hello")
    ret = ""
    try:
        body = request.get_json()
        ret = body["challenge"]
    except:
        print("no challenge")
    try:
        if body["token"] == token:
            print(str(body))
            url = body["event"]["links"][0]["url"]
            print(url)
            spot_ids = re.findall(spotify_reg, url)
            spot_id = ""
            if len(spot_ids) == 0:
                spot_id = url.split("/track/")[-1]
            else:
                spot_id = spot_ids[-1]
            print(spot_id)
            sp = spotipy.Spotify(auth=oauth_token)
            results = sp.user_playlist_add_tracks(username, playlist_id, [spot_id])
    except:
        print("no spotify song")
    return ret, 200

if __name__ == '__main__':
    # Threaded option to enable multiple instances for multiple user access support
    app.run(threaded=True, port=5000)

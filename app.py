import re
import os

from flask import request, Flask
import requests
from slack import WebClient


app = Flask(__name__)
slack_token = os.environ["SLACK_API_TOKEN"]
token = os.environ["SLACK_REQ_TOKEN"]

client = WebClient(token=slack_token)
slack_channel = "zar-test"

spotify_reg = "[^\/][\w]+(?=\?)"

@app.route('/')
def hello_world():
    return 'Hello, World!'

@app.route('/add_to_playlist', methods=['GET', 'POST'])
def add_to_playlist(): 
    print("Adding song to playlist.")
    ret = ""
    try:
        # This code path is required to validate an endpoint for slack events
        body = request.get_json()
        ret = body["challenge"]
    except:
        print("No challenge token present.")
    try:
        # 
        if body["token"] == token:
            print(str(body))
            url = body["event"]["links"][0]["url"]
            spot_ids = re.findall(spotify_reg, url)
            spot_id = ""
            if len(spot_ids) == 0:
                spot_id = url.split("/track/")[-1]
            else:
                spot_id = spot_ids[-1]
            print(spot_id)

            if ".com" not in spot_id:
                print(f"Posting Spotify song: {spot_id} to {slack_channel}")
                response = client.chat_postMessage(channel=slack_channel, text=spot_id)
    except :
        print("No spotify song found in the posted link.")
    return ret, 200

if __name__ == '__main__':
    # Threaded option to enable multiple instances for multiple user access support
    app.run(threaded=True, port=5000)

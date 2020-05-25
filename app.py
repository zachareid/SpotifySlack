from flask import request, Flask
import requests
import re
import os
from slack import WebClient
from slack.errors import SlackApiError

token = "UYXuhkMMui7Vhk4APkQ7poaL"
spotify_reg = "[^\/][\w]+(?=\?)"

app = Flask(__name__)
slack_token = os.environ["SLACK_API_TOKEN"]
client = WebClient(token=slack_token)
slack_channel = "zar-test"


@app.route('/')
def hello_world():
    return 'Hello, World!'


@app.route('/new_message4', methods=['GET', 'POST'])
def new_message4(): 
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
            print(f"spotids: {spot_ids}")
            spot_id = ""
            if len(spot_ids) == 0:
                spot_id = url.split("/track/")[-1]
            else:
                spot_id = spot_ids[-1]
            print(spot_id)

            response = client.chat_postMessage(channel=slack_channel, text=spot_id)
    except :
        print("no spotify song")
    return ret, 200

if __name__ == '__main__':
    # Threaded option to enable multiple instances for multiple user access support
    app.run(threaded=True, port=5000)

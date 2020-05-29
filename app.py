import re
import os
import time
from threading import Lock

from flask import request, Flask, jsonify
from flask_sqlalchemy import SQLAlchemy

import requests
from slack import WebClient
import yfinance as yf

from datetime import date, timedelta, datetime

app = Flask(__name__)
slack_token = os.environ["SLACK_API_TOKEN"]
token = os.environ["SLACK_REQ_TOKEN"]

app.config['SQLALCHEMY_DATABASE_URI'] = os.environ["DATABASE_URL"]
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

song_set = set()
song_lock = Lock()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    firstname = db.Column(db.String(64))
    lastname = db.Column(db.String(64))
    predictions = db.relationship('Prediction', backref='user', lazy='dynamic')
    slack_id = db.Column(db.String(64))

    def __init__(self, firstname, lastname, slack_id):
        self.firstname = firstname
        self.lastname = lastname
        self.slack_id = slack_id

    def __repr__(self):
        return f"User :{self.firstname} {self.lastname}>"

class Prediction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    stock = db.Column(db.String(10))
    prediction_start = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    prediction_end = db.Column(db.DateTime, index=True)
    prediction_days = db.Column(db.Integer)
    stock_price = db.Column(db.Float)
    stock_price_end = db.Column(db.Float)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))

    def __init__(self, stock, stock_price, prediction_start, prediction_days, user_id):
        self.stock = stock
        self.stock_price = stock_price
        self.prediction_start = prediction_start
        self.prediction_days = prediction_days
        self.prediction_end = prediction_start + timedelta(days=prediction_days)
        self.user_id = user_id

    def __repr__(self):
        out_str =  f"{self.stock}\n"
        out_str += f"\tStart date: {self.prediction_start:%Y-%m-%d} \n\tEnd Date: {self.prediction_end:%Y-%m-%d} \n\tDays: {self.prediction_days}\n"
        out_str += f"\tStart Price: ${float(self.stock_price):.02f}\n"
        if self.stock_price_end:
            out_str += f"\tEnd Price: ${float(self.stock_price_end):.02f} \n"
        return out_str


client = WebClient(token=slack_token)
slack_channel = "zar-test"

spotify_reg = "[^\/][\w]+(?=\?)"


@app.route('/')
def hello_world():
    return 'Hello, World!'

@app.route("/update_predictions", methods=['POST'])
def updatePredictions():
    preds = Prediction.query.filter(Prediction.stock_price_end == None)
    for pred in preds:
        print(f"Scanning predictions...{pred}")
        # If the current datetime is at least a day past the last prediction
        if datetime.now() > pred.prediction_end + timedelta(days=1):
            print(f"Updating prediction")
            # need to update
            closing_price = getClosingPrice(pred.stock, pred.prediction_end)
            pred.stock_price_end = closing_price
            db.session.commit()


def getPredictions(slack_id):
    user = User.query.filter(User.slack_id == slack_id).first()
    preds = user.predictions.all()
    out_str = ""
    for pred in preds:
        out_str += str(pred)
        price = getClosingPrice(pred.stock, date.today())
        out_str += f"\tCurrent Price: ${float(price):.02f}\n"
    out_json = {}
    out_json["text"] = "Predictions"
    out_json["response_type"] = "in_channel"
    out_json["attachments"] = [ { "text" : out_str}]
    return out_json
    
    

@app.route('/predict', methods=['POST'])
def predict():
    print(request.form)
    up = True
    days = 0
    command = request.form["text"]
    slack_id = request.form["user_id"]
    args = command.split(" ")

    ticker = args[0]

    if ticker == "get":
        updatePredictions()
        return jsonify(getPredictions(slack_id))
    if "$" not in ticker:
        return "You forgot the $, idiot"
    
    ticker = ticker.replace("$", "")
    
    direction = args[1]
    if direction == "up":
        up = True
    elif direction == "down":
        up = False
    else:
        return "Specify a correct direction of the stock price, you pathetic dumbfuck.", 200
    
    days_str = args[2]
    if isInt(days_str):
        days = int(days_str)
    else:
        return "Specify a correct number of days, dear Lord you're dumb."

    closing_val = getClosingPrice(ticker, date.today())
    user = User.query.filter_by(slack_id = slack_id).first()

    pred = Prediction(ticker, float(closing_val),  date.today(), days, user.id)
    print(pred)
    db.session.add(pred)
    db.session.commit()

    out_str = f"You predict that {ticker}, which is currently at ${closing_val:.2f}, will go {direction} in {days} days"
    return out_str, 200

def getClosingPrice(ticker, day):
    begin = day - timedelta(days=5)
    data = yf.download(ticker.replace("$",""), begin, day)
    closing_val = data.Close[-1]
    return closing_val


def isInt(s):
    try: 
        int(s)
        return True
    except ValueError:
        return False

@app.route('/add_to_playlist', methods=['GET', 'POST'])
def add_to_playlist(): 
    print("/add_to_playlist called")
    ret = ""
    try:
        # This code path is required to validate an endpoint for slack events
        body = request.get_json()
        ret = body["challenge"]
    except:
        print("No challenge token present.")
    try:
        if body["token"] == token:
            url = body["event"]["links"][0]["url"]
            spot_ids = re.findall(spotify_reg, url)
            spot_id = ""
            if len(spot_ids) == 0:
                spot_id = url.split("/track/")[-1]
            else:
                spot_id = spot_ids[-1]
            with song_lock:
                if spot_id in song_set:
                    ret = "Already in playlist"
                    return ret, 200
                else:
                    song_set.add(spot_id)
            if ".com" not in spot_id:
                response = client.chat_postMessage(channel=slack_channel, text=spot_id)
    except :
        print("No spotify song found in the posted link.")
    return ret, 200

if __name__ == '__main__':
    # Threaded option to enable multiple instances for multiple user access support
    app.run(port=5000)

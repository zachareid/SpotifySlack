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


def getCurrentPrice(ticker):
    return getClosingPrice(ticker, datetime.now())

def getClosingPrice(ticker, day):
    begin = day - timedelta(days=5)
    data = yf.download(ticker.replace("$",""), begin, day)
    closing_val = data.Close[-1]
    return closing_val


def getHoldings(slack_id):
    user = User.query.filter(User.slack_id == slack_id).first()
    stocks = user.stocks.all()
    out_str = "Holdings:\n"
    for stock in stocks:
        out_str += "\t" + str(stock) + "\n"
    out_json = {}
    out_json["text"] = out_str
    out_json["response_type"] = "in_channel"
    return out_json

def getHoldingsAll():
    users = User.query.all()
    out_str = "Holdings:\n"
    for user in users:
        out_str += f"User: {user.firstname}\n"
        stocks = user.stocks.all()
        for stock in stocks:
            out_str += "\t" + str(stock) + "\n"
    out_json = {}
    out_json["text"] = out_str
    out_json["response_type"] = "in_channel"
    return out_json




@app.route('/buy', methods = ['POST'])
def purchase():
    command = request.form["text"]
    slack_id = request.form["user_id"]
    args = command.split(" ")
    ticker = args[0]
    ticker = ticker.replace("$", "")
    try:
        shares = int(args[1])
        if shares < 1:
            return "Enter a real number of stocks dumbfuck"
    except:
        return "Enter a real number of stocks dumbfuck"
    buyStock(slack_id, ticker, shares)
    return "Successfully purchases"


def buyStock(slack_id, ticker, shares):
    try:
        price = getCurrentPrice(ticker)
    except:
        return "Not a real stock, dumbass"
    ticker = ticker.lower()
    user = User.query.filter_by(slack_id = slack_id).first()
    cash = user.cash
    purchase_total = price * shares
    if cash > purchase_total:
        holding = StockHolding.query.filter(StockHolding.ticker==ticker).filter(StockHolding.user_id==user.id).first()
        if not holding:
            holding = StockHolding(shares, ticker, price, user.id)
        else:
            holding.num_shares += shares
        user.cash = user.cash - purchase_total
        db.session.add(holding)
        db.session.add(user)
        db.session.commit()
    else:
        return "hey broke ass, you don't have enough money"


def sellStock(slack_id, ticker, shares):
    try:
        price = getCurrentPrice(ticker)
    except:
        return "Not a real stock, dumbass"
    ticker = ticker.lower()
    user = User.query.filter(User.slack_id == slack_id).first()
    holding = StockHolding.query.filter(StockHolding.ticker==ticker).filter(StockHolding.user_id==user.id).first()
    if not holding:
        return "You don't own any of this stock"
    elif holding.num_shares < shares:
        return "not enough shares"
    else:
        shares_left = holding.num_shares - shares
        holding.num_shares = shares_left
        user.cash += shares * price
        if shares_left == 0:
            db.session.delete(holding)
        db.session.add(user)
        db.session.commit()


@app.route('/sell', methods = ['POST'])
def sell():
    command = request.form["text"]
    slack_id = request.form["user_id"]
    args = command.split(" ")
    ticker = args[0]
    ticker = ticker.replace("$", "").lower()
    try:
        shares = int(args[1])
        if shares < 1:
            "Enter a real number of stocks dumbfuck"
    except:
        return "Enter a real number of stocks dumbfuck"
    sellStock(slack_id, ticker, shares)
    return "Successfully sold stock"

@app.route('/portfolio', methods=["POST"])
def getPortfolio():
    slack_id = request.form["user_id"]
    return getHoldings(slack_id)

@app.route('/portfolios', methods=["POST"])
def getPortfolios():
    return getHoldingsAll()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    firstname = db.Column(db.String(64))
    lastname = db.Column(db.String(64))
    cash = db.Column(db.Float, default=0)
    stocks = db.relationship('StockHolding', backref='user', lazy='dynamic')
    slack_id = db.Column(db.String(64))

    def __init__(self, firstname, lastname, slack_id):
        self.firstname = firstname
        self.lastname = lastname
        self.slack_id = slack_id

    def __repr__(self):
        return f"User :{self.firstname} {self.lastname}, ${self.cash:.02f}, stocks: {self.stocks.all()}"

class StockHolding(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    num_shares = db.Column(db.Integer)
    ticker = db.Column(db.String(10))
    purchase_price = db.Column(db.Float)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    def __init__(self, num_shares, ticker, purchase_price, user_id):
        self.num_shares = num_shares
        self.ticker = ticker
        self.purchase_price = purchase_price
        self.user_id = user_id
    def __repr__(self):
        return f"Stock: {self.ticker.upper()}, {self.num_shares} shares."






song_lock = Lock()
song_list_length = 1000
song_list = [None] * song_list_length
song_ind = 0

def add_to_songlist(elem):
    global song_ind
    song_list[song_ind] = elem
    song_ind = (song_ind + 1) % song_list_length

client = WebClient(token=slack_token)
slack_channel = "zar-test"

spotify_reg = "[^\/][\w]+(?=\?)"


@app.route('/')
def hello_world():
    return 'Hello, World!'

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
                if spot_id in song_list:
                    ret = "Already in playlist"
                    return ret, 200
                else:
                    add_to_songlist(spot_id)
            if ".com" not in spot_id:
                response = client.chat_postMessage(channel=slack_channel, text=spot_id)
    except :
        print("No spotify song found in the posted link.")
    return ret, 200



if __name__ == '__main__':
    # Threaded option to enable multiple instances for multiple user access support
    app.run(port=5000)

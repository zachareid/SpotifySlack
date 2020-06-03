test_ids = [str(i) for i in range(40)]

song_list_length = 12
song_list = [None] * song_list_length
song_ind = 0

def add_song_to_list(elem):
    global song_ind
    song_list[song_ind] = elem
    song_ind = (song_ind + 1) % song_list_length


[add_song_to_list(elem) for elem in test_ids]


import threading
import yfinance as yf
import time

from app import getCurrentPrice


def getCurrentPriceThread(ticker, res):
    res.append(getCurrentPrice(ticker))



def test_threaded_priceUpdate(num_stonks):
    res = []
    t1 = time.time()
    thread_list = []
    for i in range(num_stonks):
        thread = threading.Thread(target=getCurrentPriceThread, args=("aapl",res))
        thread_list.append(thread)
    for thread in thread_list:
        thread.start()
    for thread in thread_list:
        thread.join()

    print(time.time() - t1)
    return res
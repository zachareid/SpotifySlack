test_ids = [str(i) for i in range(40)]

song_list_length = 12
song_list = [None] * song_list_length
song_ind = 0

def add_song_to_list(elem):
    global song_ind
    song_list[song_ind] = elem
    song_ind = (song_ind + 1) % song_list_length


[add_song_to_list(elem) for elem in test_ids]

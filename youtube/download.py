'''Downloading youtube content for PERSONAL USE'''
# importing the module
import re
import os
from pytube import YouTube
from pytube import Playlist

VIDEO_SAVE_PATH = "mp4"
AUDIO_SAVE_PATH = "mp3"

# Set the value to mp3 or mp4 depening on what you wish to download
# mp3 just audio in mp3 format
# mp4 video
OUTPUT="mp4"

def main():
    '''
    This function downloads video or audio stream from youtube
    '''
    url = str(input("Url you want to download: "))
    check_dir(VIDEO_SAVE_PATH)
    check_dir(AUDIO_SAVE_PATH)

    if re.search('playlist?list',url):
        videos=read_playlist(url)
    else:
        videos=[url]

    for file_url in videos:
        if OUTPUT=="mp3":
            download_audio(file_url)
        else:
            download_video(url)

def read_playlist(pl_list):
    '''Gathering all the individual urls from a playlist url
    @input:
    :pl_list string: the playlist url you wish to download

    @output:
    :dictionary: all the urls of videos are included in playlist
    '''
    playlist = Playlist(pl_list)
    playlist._video_regex = re.compile(r"\"url\":\"(/watch\?v=[\w-]*)")
    return playlist.video_urls

def download_video(url):
    '''Downloading the video
    @input:
    :url string: the url of the video you want to download
    @output:
    :the video itself
    '''
    yt_video = YouTube(url)
    title = yt_video.title
    yt_video.streams.filter(progressive=True, file_extension='mp4')\
        .order_by('resolution')\
        .desc()\
        .first()\
        .download(VIDEO_SAVE_PATH)
    print(f"{title} is downloaded")

def download_audio(url):
    '''Downloading only audio stream into mp3
    @input:
    :link string: the link of the video you want to download
    @output:
    :the the audio stream itself
    '''
    yt_audio = YouTube(url)
    title = yt_audio.title
    video = yt_audio.streams.filter(only_audio=True).first()
    downloaded_file = video.download(AUDIO_SAVE_PATH)
    base = os.path.splitext(downloaded_file)[0]
    new_file = base + '.mp3'
    os.rename(downloaded_file, new_file)
    print(f"{title} is downloaded")

def check_dir(target_dir):
    '''Checking if the target directory exists
    @input:
    :target_dir string: the name(path) of the target directory
    '''
    if not os.path.exists(target_dir):
        os.makedirs(target_dir)


if __name__ == "__main__":
    main()

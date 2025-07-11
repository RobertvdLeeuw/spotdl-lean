import os

from spotdl import Spotdl
from spotdl.types.options import DownloaderOptions, DownloaderOptionalOptions

DOWNLOAD_LOC = "./downloads"

import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from spotdl import Spotdl

# Test injection method
credentials = SpotifyClientCredentials(
    client_id="a766651ba4b744ed82f1e520a75b2455",
    client_secret="767732da0b064b838ebe5d0e3f6ce4eb",
)
spotify_client = spotipy.Spotify(client_credentials_manager=credentials)

spotdl = Spotdl(spotify_client=spotify_client,
                downloader_settings=DownloaderOptions(format="wav",
                                                      simple_tui=False,
                                                      print_download_errors=False,
                                                      output=DOWNLOAD_LOC)
                )

# spotdl = Spotdl(
#     no_cache=True,
#     client_id="a766651ba4b744ed82f1e520a75b2455",
#     client_secret="767732da0b064b838ebe5d0e3f6ce4eb",
# )

spotify_id = "3dzCClyQ3qKx2o3CLIx02r"
song = spotdl.search([f"https://open.spotify.com/track/{spotify_id}"])[0]

if not song:
    print(f"No song found for id: {spotify_id}")
    exit()

print(f"Song found: {song.name} by {song.artist}")

x, file_path = spotdl.download(song)
print(x, file_path)
# _, file_path = downloader.download_song(song)

if not file_path or not os.path.exists(file_path):
    print(f"Download of {spotify_id} completed but file not found: {file_path}")
    raise Exception(f"Download of {spotify_id} completed but file not found: {file_path}")

file_size = os.path.getsize(file_path)
print(f"Download completed: {file_path} ({file_size / (1024*1024):.2f} MB).")

print(f"Downloading song '{file_path}' successful.")

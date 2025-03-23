import base64
import gzip
import io
import logging
import os
import sys
import xmlrpc.client

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
proxy = xmlrpc.client.ServerProxy("https://api.opensubtitles.org:443/xml-rpc")
token = proxy.LogIn(sys.argv[1], sys.argv[2], "", sys.argv[3])["token"]
movies_path = "/movies"


class Movie:
    def __init__(self, directory_name: str):
        self.directory_name = directory_name
        self.title, self.id = directory_name.split(".tt")


class Subtitle:
    def __init__(self, sub_info: dict[str, str]):
        self.id = sub_info["IDSubtitleFile"]
        self.downloads = int(sub_info["SubDownloadsCnt"])


def main():
    movies = [Movie(dir_name) for dir_name in os.listdir(movies_path)]

    for movie in movies:
        get_subs(movie)


def get_subs(movie: Movie):
    if not has_subs(movie):
        download_subs(movie)
    return ""


def has_subs(movie: Movie) -> bool:
    if movie.id == "0000000":
        return True

    path = f"{movies_path}/{movie.directory_name}"
    if os.path.isdir(path):
        return len(os.listdir(path)) > 1
    return True


def download_subs(movie: Movie) -> None:
    logging.info(f"Downloading subtitles for {movie.title}")
    subs = find_subs(movie)
    counter = 0
    for subtitle in subs:
        if counter == 5:
            break

        counter += download_sub(movie, subtitle, counter)

    logging.info(f"Downloaded {counter} subtitles for {movie.title}")


def find_subs(movie: Movie) -> list[Subtitle]:
    try:
        search_parameters = {"imdbid": movie.id, "sublanguageid": "eng", "subformat": "srt", "subencoding": "utf-8"}
        subtitles = [Subtitle(sub) for sub in proxy.SearchSubtitles(token, [search_parameters])["data"]]
        subtitles.sort(reverse=True, key=lambda sub: sub.downloads)

        return subtitles
    except Exception as e:
        logging.error("Failed to search for subtitle: %s", e)
        return []


def download_sub(movie: Movie, subtitle: Subtitle, counter: int) -> int:
    try:
        download = proxy.DownloadSubtitles(token, [subtitle.id])["data"]
        if len(download) > 1:
            raise RuntimeError("Subtitle contained multiple files")

        base64_data = download[0]["data"]
        binary_data = base64.b64decode(base64_data)

        with gzip.GzipFile(fileobj=io.BytesIO(binary_data)) as decompressed_file:
            file_data = decompressed_file.read()

        with open(f"{movies_path}/{movie.title}.tt{movie.id}/{movie.title}.{counter}.srt", "wb+") as output_file:
            output_file.write(file_data)

        return 1
    except Exception as e:
        logging.error("Failed to download subtitle: %s", e)
        return 0


main()

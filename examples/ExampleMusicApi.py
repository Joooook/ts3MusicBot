from urllib.parse import urlencode
from typing import Dict, Union, List
import requests

from apis.muiscApi.MusicApi import MusicApiResponse, MusicApi, api
from apis.muiscApi.data import PlayList, Song, Album, Singer



class ExampleMusicApi(MusicApi):

    def __init__(self,url,type):
        self.type = type
        super().__init__(url)

    @staticmethod
    def _gen_song(song_data):
        song = Song(id=song_data['ID'], name=song_data['title'],
                    singers=[Singer(id=singer['ID'], name=singer['name']) for singer in song_data['singers']])
        if song_data['album']['ID'] != '0':
            song.album = Album(id=song_data['album']['ID'], name=song_data['album']['name'])
        return song

    # 以下api需要根据不同的api调整。
    @api
    def available(self):
        response = self.search_songs("陈奕迅")
        if not response.succeed:
            return response
        if not response.data:
            return MusicApiResponse.failure("Unavailable")
        return MusicApiResponse.success()

    @api
    def search_songs(self, key: str, size: int = 20, max_retries: int = 2) -> MusicApiResponse:
        search_url = self.url + f"/api/music/{self.type}/search"
        params = {"key": key, "pageIndex": 1, "pageSize": size}
        rep = None
        for _ in range(max_retries):
            try:
                rep = requests.get(search_url, params=params)
                break
            except Exception:
                continue
        if rep is None:
            raise requests.exceptions.RequestException
        if 'data' in rep.json()['data']:
            data = rep.json()['data']['data']
            songs=[]
            for song_data in data:
                songs.append(self._gen_song(song_data))
            return MusicApiResponse.success(songs)
        return MusicApiResponse.success([])

    @api
    def get_songs(self, ids:Union[str,list]):
        if type(ids) is str:
            ids=[ids]
        url = self.url + f"/api/music/{self.type}/song"
        params = {"ID": ','.join(ids)}
        rep = requests.get(url, params=params)
        data = rep.json()['data']
        songs = []
        for song_data in data:
            song = self._gen_song(song_data)
            songs.append(song)
        return MusicApiResponse.success(songs)

    @api
    def get_suggest(self, key, max_retries: int = 2):
        suggest_url = self.url + f"/api/music/{self.type}/searchsuggest"
        params = {"key": key}
        rep = None
        for _ in range(max_retries):
            try:
                rep = requests.get(suggest_url, params=params)
                break
            except Exception:
                continue
        if rep is None:
            raise requests.exceptions.RequestException
        if 'search' in rep.json()['data']:
            suggestions = rep.json()['data']['search']
            return MusicApiResponse.success(suggestions)
        return MusicApiResponse.success([])

    @api
    def get_song_link(self, song_id: str, quality: int = 320, file_format: str = "mp3"):
        url = self.url + f"/api/music/{self.type}/url"
        params = {"ID": song_id, "quality": quality, "format": file_format}
        return MusicApiResponse.success(url + "?" + urlencode(params))

    @api
    def get_avatar_link(self, song_id: str, quality: int = 500, file_format: str = "jpg"):
        url = self.url + f"/api/music/{self.type}/url"
        params = {"ID": song_id, "quality": quality, "format": file_format}
        return MusicApiResponse.success(url + "?" + urlencode(params))




if __name__ == '__main__':
    print(MusicApi("https://xxx.com","xxxx").search_songs("陈奕迅"))

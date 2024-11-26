import copy
import json
import os
import re
from urllib.parse import urlencode
from typing import Dict, Union, List
import requests

from apis.BaseApi import BaseApiResponse
from apis.muiscApi.data import PlayList, Song, Album, Singer
from apis.muiscApi.exceptions import MusicApiException


class MusicApiResponse(BaseApiResponse):
    pass

def api(func):
    def wrapper(*args, **kwargs) -> MusicApiResponse:
        try:
            return func(*args, **kwargs)
        except requests.exceptions.RequestException:
            return MusicApiResponse.failure("NetworkError")
        except MusicApiException:
            return MusicApiResponse.failure("MusicApiError")
        except Exception as e:
            return MusicApiResponse.failure(f"UnknownError: {type(e)} {e}")
    return wrapper

class MusicApi:
    def __init__(self, url, api_type):
        self.url = url
        self.type = api_type
        self.playlists_path='./playlists.json'
        self.current_list_id = 'current'
        self.current_index = -1
        self.playlists:Dict[str,PlayList] = {}
        self.init_playlists()

    def init_playlists(self):
        if os.path.exists(self.playlists_path):
            data = json.load(open(self.playlists_path))
            for playlist_id,playlist in data.items():
                self.playlists[playlist_id]=PlayList(**playlist)
        else:
            self.playlists = {}
        if self.current_list_id not in self.playlists.keys():
            self.playlists[self.current_list_id] = PlayList(id=self.current_list_id, songs=[])
        return

    def save_playlists(self):
        # 尽量只在对list进行操作的接口中执行
        data = {}
        for playlist_id,playlist in self.playlists.items():
            data[playlist_id] = json.loads(playlist.model_dump_json())
        with open(self.playlists_path, 'w') as f:
            f.write(json.dumps(data))
        return

    def _gen_song(self,song_data):
        song = Song(id=song_data['ID'], name=song_data['title'], link=self.get_song_link(song_data['ID']).data,
                    singers=[Singer(id=singer['ID'], name=singer['name']) for singer in song_data['singers']])
        if song_data['album']['ID'] != '0':
            song.album = Album(id=song_data['album']['ID'], name=song_data['album']['name'])
        return song

    @api
    def list_create(self, list_id: str):
        if list_id in self.playlists.keys():
            return MusicApiResponse.failure("歌单Id已存在。")
        self.playlists[list_id] = PlayList(id=list_id, songs=[])
        self.save_playlists()
        return MusicApiResponse.success()

    @api
    def list_play(self, list_id: str):
        if list_id not in self.playlists.keys():
            return MusicApiResponse.failure("歌单未找到。")
        self.current_copy(list_id)
        self.current_index = 0
        return MusicApiResponse.success()

    @api
    def list_copy(self, list_src: str,list_dst: str):
        if list_src not in self.playlists.keys():
            return MusicApiResponse.failure("歌单未找到。")
        self.playlists[list_dst] = PlayList(id=list_dst,songs=self.playlists[list_src].songs)
        self.save_playlists()
        return MusicApiResponse.success()

    @api
    def list_show(self, list_id: str):
        if list_id not in self.playlists.keys():
            return MusicApiResponse.failure("歌单未找到。")
        return MusicApiResponse.success(self.playlists[list_id])

    @api
    def list_list(self):
        tmp_playlists = copy.copy(self.playlists)
        tmp_playlists.pop(self.current_list_id)
        if len(tmp_playlists.keys()) == 0:
            return MusicApiResponse.failure("未创建任何歌单。")
        return MusicApiResponse.success(tmp_playlists)

    @api
    def list_delete(self, list_id: str):
        if list_id not in self.playlists.keys():
            return MusicApiResponse.failure("歌单未找到。")
        self.playlists.pop(list_id)
        self.save_playlists()
        return MusicApiResponse.success()

    @api
    def list_add(self, list_id: str, songs:Union[Song,List[Song]]):
        if list_id not in self.playlists.keys():
            return MusicApiResponse.failure("歌单未找到。")
        if type(songs) is Song:
            songs = [songs]
        self.playlists[list_id].songs+=songs
        self.save_playlists()
        return MusicApiResponse.success()

    @api
    def list_remove(self, list_id: str, index:int):
        if list_id not in self.playlists.keys():
            return MusicApiResponse.failure("歌单未找到。")
        try:
            self.playlists[list_id].songs.pop(index)
        except IndexError:
            return MusicApiResponse.failure("索引超出范围。")
        self.save_playlists()
        return MusicApiResponse.success()

    @api
    def list_insert(self, list_id: str, index: int, song:Song):
        if list_id not in self.playlists.keys():
            return MusicApiResponse.failure("歌单未找到。")
        try:
            self.playlists[list_id].songs.insert(index,song)
        except IndexError:
            return MusicApiResponse.failure("索引超出范围。")
        self.save_playlists()
        return MusicApiResponse.success()

    @api
    def list_clear(self, list_id: str):
        if list_id not in self.playlists.keys():
            return MusicApiResponse.failure("歌单未找到。")
        self.playlists[list_id].songs.clear()
        self.save_playlists()
        return MusicApiResponse.success()

    @api
    def is_list_empty(self, list_id: str):
        if list_id not in self.playlists.keys():
            return MusicApiResponse.failure("歌单未找到。")
        if len(self.playlists[list_id].songs) == 0:
            return MusicApiResponse.success(True)
        return MusicApiResponse.success(False)

    @api
    def is_list_created(self, list_id: str):
        if list_id not in self.playlists.keys():
            return MusicApiResponse.success(False)
        return MusicApiResponse.success(True)

    # @api
    # def list_remove(self, list_id: str, links: Union[int, list[int]]):
    #     if list_id not in self.playlists.keys():
    #         return MusicApiResponse.failure("歌单未找到")
    #     if links is str:
    #         links = [links]
    #     ids = []
    #     for link in links:
    #         ids.append(re.findall(r"ID=(\d+)", link))
    #     response = self.get_songs(ids)
    #     if not response.succeed:
    #         return response
    #     self.playlists[list_id].songs.append(response.data)
    #     return MusicApiResponse.success()

    @api
    def search_songs(self, key: str, page_index: int = 1, page_size: int = 20, max_retries: int = 2):
        search_url = self.url + f"/api/music/{self.type}/search"
        params = {"key": key, "pageIndex": page_index, "pageSize": page_size}
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
    def get_info(self, song_id):
        get_info_url = self.url + f"/api/music/{self.type}/song"
        params = {"ID": song_id}
        rep = requests.get(get_info_url, params=params)
        return MusicApiResponse.success(rep.json()['data'])

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

    @api
    def current_insert(self,song:Song):
        return self.list_insert(self.current_list_id, self.current_index, song)

    @api
    def current_add(self, song: Song):
        return self.list_add(self.current_list_id, song)

    @api
    def current_copy(self, list_id):
        return self.list_copy(list_id, self.current_list_id)

    @api
    def current_show(self):
        return self.list_show(self.current_list_id)

    @api
    def is_current_empty(self):
        return self.is_list_empty(self.current_list_id)

    @api
    def next(self):
        if self.is_current_empty().data:
            return MusicApiResponse.failure("当前歌单为空。")
        self.current_index = (self.current_index + 1) % len(self.playlists[self.current_list_id].songs)
        return self.now()

    @api
    def previous(self):
        if self.is_current_empty().data:
            return MusicApiResponse.failure("当前歌单为空。")
        self.current_index = (self.current_index - 1) % len(self.playlists[self.current_list_id].songs)
        return self.now()

    @api
    def jump(self,index:int):
        if self.is_current_empty().data:
            return MusicApiResponse.failure("当前歌单为空。")
        if index<0 or index >= len(self.playlists[self.current_list_id].songs):
            return MusicApiResponse.failure("索引超出范围。")
        self.current_index = index
        return self.now()

    @api
    def clear(self):
        self.list_clear(self.current_list_id)
        return MusicApiResponse.success()

    @api
    def now(self):
        if self.is_current_empty().data:
            return MusicApiResponse.failure("当前歌单为空。")
        if self.current_index == -1 :
            return MusicApiResponse.failure("还未开始播放。")
        return MusicApiResponse.success(self.playlists[self.current_list_id].songs[self.current_index])




if __name__ == '__main__':
    print(MusicApi("https://xxx.com","xxxx").search_songs("陈奕迅"))

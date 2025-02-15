import copy
import json
import os
from abc import ABC, abstractmethod
from urllib.parse import urlencode
from typing import Dict, Union, List
import requests
import random

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

class MusicApi(ABC):
    def __init__(self, url):
        self.url = url
        self.playlists_path=f'./{self.__class__.__name__}_playlists.json'
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

    # 以下api需要根据不同的api调整。
    @api
    @abstractmethod
    def available(self):
        pass

    @api
    @abstractmethod
    def search_songs(self, key: str, size: int = 20, max_retries: int = 2):
        pass

    @api
    @abstractmethod
    def get_songs(self, ids:Union[str,list]):
        pass

    @api
    @abstractmethod
    def get_suggest(self, key):
        pass

    @api
    @abstractmethod
    def get_song_link(self, song_id: str, quality: int = 320, file_format: str = "mp3") -> MusicApiResponse:
        pass

    @api
    @abstractmethod
    def get_avatar_link(self, song_id: str, quality: int = 500, file_format: str = "jpg") -> MusicApiResponse:
        pass

    @api
    def current_insert(self,song:Song):
        return self.list_insert(self.current_list_id, self.current_index, song)

    @api
    def current_add(self, song: Song):
        return self.list_add(self.current_list_id, song)

    @api
    def current_remove(self, index: int):
        return self.list_remove(self.current_list_id, index)

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

    @api
    def shuffle(self):
        if self.is_current_empty().data:
            return MusicApiResponse.failure("当前歌单为空。")
        random.shuffle(self.playlists[self.current_list_id].songs)
        return MusicApiResponse.success()

if __name__ == '__main__':
    print(MusicApi("https://xxx.com").search_songs("陈奕迅"))

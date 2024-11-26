import urllib.parse

import requests

from apis.BaseApi import BaseApiResponse
from apis.audioBotApi.exceptions import AudioBotApiException


class AudioBotApiResponse(BaseApiResponse):
    pass


# ERROR：关于error的reason，主要要分辨是远端的AudioBot的问题还是本端的网络问题还是数据处理问题。
# 装饰器
def api(func):
    def wrapper(*args, **kwargs) -> AudioBotApiResponse:
        try:
            return func(*args, **kwargs)
        except requests.exceptions.RequestException:
            return AudioBotApiResponse.failure("NetworkError")
        except AudioBotApiException:
            return AudioBotApiResponse.failure("AudioBotError")

    return wrapper


class AudioBotApi:
    def __init__(self, url, bot_id=0):
        self.url = url
        self.bot_id = bot_id

    @api
    def exec(self, *args, encode_all=True):
        if encode_all:
            urlencoded_args = map(lambda x: urllib.parse.quote(x, encoding='UTF-8', safe=''), args)
        else:
            urlencoded_args = map(lambda x: urllib.parse.quote(x, encoding='UTF-8'), args)
        url = self.url + f"/api/bot/use/{self.bot_id}/(/" + '/'.join(urlencoded_args)
        rep = requests.get(url)
        return AudioBotApiResponse.success(rep)

    # 无返回数据的api

    @api
    def add(self, link: str):
        response = self.exec("add", link)
        rep: requests.models.Response = response.data
        if rep.status_code != 204:
            return AudioBotApiResponse.failure(f"状态码错误：{rep.status_code}")
        return AudioBotApiResponse.success()

    @api
    def list_add(self, list_id: str, link: str):
        response = self.exec("list", "add", list_id, link)
        rep: requests.models.Response = response.data
        if rep.status_code != 204:
            return AudioBotApiResponse.failure(f"状态码错误：{rep.status_code}")
        return AudioBotApiResponse.success()

    @api
    def play(self, link: str = ''):
        response = self.exec("play", link)
        rep: requests.models.Response = response.data
        if rep.status_code != 204 and rep.status_code != 200:
            return AudioBotApiResponse.failure(f"状态码错误：{rep.status_code}")
        return AudioBotApiResponse.success()

    @api
    def pause(self):
        response = self.exec("pause")
        rep: requests.models.Response = response.data
        if rep.status_code != 204:
            return AudioBotApiResponse.failure(f"状态码错误：{rep.status_code}")
        return AudioBotApiResponse.success()

    @api
    def previous(self):
        response = self.exec("previous")
        rep: requests.models.Response = response.data
        if rep.status_code != 204:
            return AudioBotApiResponse.failure(f"状态码错误：{rep.status_code}")
        return AudioBotApiResponse.success()

    @api
    def next(self):
        response = self.exec("next")
        rep: requests.models.Response = response.data
        if rep.status_code != 204:
            return AudioBotApiResponse.failure(f"状态码错误：{rep.status_code}")
        return AudioBotApiResponse.success()

    @api
    def jump(self, index: int):
        response = self.exec("jump", str(index))
        rep: requests.models.Response = response.data
        if rep.status_code != 204:
            return AudioBotApiResponse.failure(f"状态码错误：{rep.status_code}")
        return AudioBotApiResponse.success()

    @api
    def seek(self, position: float):
        response = self.exec("seek", str(position))
        rep: requests.models.Response = response.data
        if rep.status_code != 204:
            return AudioBotApiResponse.failure(f"状态码错误：{rep.status_code}")
        return AudioBotApiResponse.success()

    @api
    def clear(self):
        response = self.exec("clear")
        rep: requests.models.Response = response.data
        if rep.status_code != 204:
            return AudioBotApiResponse.failure(f"状态码错误：{rep.status_code}")
        return AudioBotApiResponse.success()

    @api
    def stop(self):
        response = self.exec("stop")
        rep: requests.models.Response = response.data
        if rep.status_code != 204:
            return AudioBotApiResponse.failure(f"状态码错误：{rep.status_code}")
        return AudioBotApiResponse.success()

    @api
    def is_playing(self):
        response = self.exec("song")
        rep: requests.models.Response = response.data
        if rep.status_code == 422 and rep.json()['ErrorCode'] == 10:
            return AudioBotApiResponse.success(False)
        elif rep.status_code == 200 and rep.json()['Length'] == 0.0:
            return AudioBotApiResponse.success(False)
        elif rep.status_code == 200:
            return AudioBotApiResponse.success(True)
        return AudioBotApiResponse.failure("未能获取状态。")

    # 设置属性用set开头
    @api
    def set_bot_avatar(self, link: str):
        response = self.exec("bot", "avatar", "set", link)
        rep: requests.models.Response = response.data
        if rep.status_code != 204:
            return AudioBotApiResponse.failure(f"状态码错误：{rep.status_code}")
        return AudioBotApiResponse.success()

    @api
    def set_bot_description(self, text: str):
        response = self.exec("bot", "description", "set", text)
        rep: requests.models.Response = response.data
        if rep.status_code != 204:
            return AudioBotApiResponse.failure(f"状态码错误：{rep.status_code}")
        return AudioBotApiResponse.success()

    # 有返回数据的api请使用get开头。

    @api
    def get_song(self):
        response = self.exec("song")
        rep: requests.models.Response = response.data
        if rep.status_code != 200:
            return AudioBotApiResponse.failure(f"状态码错误：{rep.status_code}")
        return AudioBotApiResponse.success(rep.json())

    @api
    def get_current(self):
        response = self.exec("song")
        rep: requests.models.Response = response.data
        if rep.status_code != 200:
            return AudioBotApiResponse.failure(f"状态码错误：{rep.status_code}")
        return AudioBotApiResponse.success(rep.json())

    @api
    def get_uid(self):
        response = self.exec("bot", "info", "client")
        rep: requests.models.Response = response.data
        if rep.status_code != 200:
            return AudioBotApiResponse.failure(f"状态码错误：{rep.status_code}")
        return AudioBotApiResponse.success(rep.json()['Uid'])

    @api
    def get_clid(self):
        response = self.exec("bot", "info", "client")
        rep: requests.models.Response = response.data
        if rep.status_code != 200:
            return AudioBotApiResponse.failure(f"状态码错误：{rep.status_code}")
        return AudioBotApiResponse.success(rep.json()['Id'])

    @api
    def get_cid(self):
        response = self.exec("bot", "info", "client")
        rep: requests.models.Response = response.data
        if rep.status_code != 200:
            return AudioBotApiResponse.failure(f"状态码错误：{rep.status_code}")
        return AudioBotApiResponse.success(rep.json()['Channel'])

    @api
    def get_list_ids(self):
        response = self.exec('list', 'list')
        rep: requests.models.Response = response.data
        if rep.status_code != 200:
            return AudioBotApiResponse.failure(f"状态码错误：{rep.status_code}")
        res = [i['Id'] for i in rep.json()]
        return AudioBotApiResponse.success(res)

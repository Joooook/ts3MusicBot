from urllib.parse import urlencode, urljoin

import requests

from apis.BaseApi import BaseApiResponse, BaseApi
from apis.ttsApi.exceptions import TTSApiException

class TTSApiResponse(BaseApiResponse):
    pass


# 装饰器
def api(func):
    def wrapper(*args, **kwargs) -> TTSApiResponse:
        try:
            return func(*args, **kwargs)
        except requests.exceptions.RequestException:
            return TTSApiResponse.failure("NetworkError")
        except TTSApiException:
            return TTSApiResponse.failure("TTSApiError")
    return wrapper


class TTSApi(BaseApi):
    def __init__(self,url:str):
        self.url = url.strip("/")

    # 参考 https://czyt.tech/post/a-free-tts-api/
    @api
    def get(self,text,voice_id:str="ppangf_csn",speed:int=1,volume:int=50,audio_type="wav") -> TTSApiResponse:
        params = {"voiceId":voice_id,"text":text,"speed":speed,"volume":volume,"audioType":audio_type}
        link = urljoin(self.url,'?'+urlencode(params))
        return TTSApiResponse.success(link)





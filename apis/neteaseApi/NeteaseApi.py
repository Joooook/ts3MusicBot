import requests

# 弃用
class NeteaseApi:
    def __init__(self,host):
        self.host=host
    def get_list(self,id):
        url=self.host+"/playlist/track/all"
        params={"id":id}
        try:
            rep=requests.get(url,params=params)
            if rep.json()['code'] == 200:
                songs = rep.json()['songs']
                id_list = [song['id'] for song in songs]
                song_list=self.get_songs(id_list)
                return song_list
        except Exception:
            return None
        return None

    def get_songs(self,ids:list):
        url=self.host+"/song/url/v1"
        params={"id":','.join(map(str,ids)),'level':'standard'}
        print(ids)
        try:
            rep=requests.get(url,params=params)
            if rep.json()['code'] == 200:
                songs = [song['url'] for song in rep.json()['data']]
                return songs
        except Exception:
            return None
        return None
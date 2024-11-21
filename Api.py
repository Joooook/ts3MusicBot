from urllib.parse import urlencode

import requests


class Api:
    def __init__(self,url,api_type):
        self.url=url
        self.type=api_type

    def search_get(self, key:str, page_index:int=1, page_size:int=20):
        songs=self.search(key=key, page_index=page_index, page_size=page_size)
        song_links=[]
        for song in songs:
            song_links.append(self.get_song(song['ID']))
        return song_links

    def search(self, key:str, page_index:int=1, page_size:int=20, max_retries:int=2):
        search_url=self.url+f"/api/music/{self.type}/search"
        params={"key":key,"pageIndex":page_index,"pageSize":page_size}
        rep=None
        for _ in range(max_retries):
            try:
                rep=requests.get(search_url,params=params)
                break
            except Exception as e:
                continue
        if rep is None:
            return None
        if 'data' in rep.json()['data']:
            songs=rep.json()['data']['data']
            return songs
        return []

    def suggest(self,key, max_retries:int=2):
        suggest_url = self.url + f"/api/music/{self.type}/searchsuggest"
        params = {"key": key}
        rep = None
        for _ in range(max_retries):
            try:
                rep = requests.get(suggest_url, params=params)
                break
            except Exception as e:
                continue
        if rep is None:
            return None
        if 'search' in rep.json()['data']:
            suggestions = rep.json()['data']['search']
            return suggestions
        return []

    def get_song(self, song_id:int, quality:int=320, file_format:str= "mp3"):
        get_url=self.url+f"/api/music/{self.type}/url"
        params={"ID":song_id,"quality":quality,"format":file_format}
        return get_url+"?"+urlencode(params)

    def get_avatar(self, song_id:int, quality:int=500, file_format:str= "jpg"):
        get_url=self.url+f"/api/music/{self.type}/url"
        params={"ID":song_id,"quality":quality,"format":file_format}
        return get_url+"?"+urlencode(params)

if __name__ == '__main__':
    print(Api().search_get("陈奕迅"))
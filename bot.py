import urllib
from urllib.parse import urlencode

import requests
import ts3
from ts3.query import TS3Connection, TS3TimeoutError
from ts3.response import TS3Event

from Api import Api

cmd_alias = {"我要听": "play", "搜索": "search", "暂停": "pause", "播放": "play", "怎么玩": "help", "帮助": "help"}


class AudioBot:
    def __init__(self, username, password, uid, bot_api, api: Api, host, port=10011):
        self.uid = uid
        self.username = username
        self.password = password
        self.host = host
        self.port = port
        self.api = api
        self.bot_api = bot_api
        self.conn: TS3Connection = None

    def listen(self):
        if self.conn is None:
            self.conn = ts3.query.TS3Connection(self.host, self.port)
        else:
            self.conn.close()
            self.conn = ts3.query.TS3Connection(self.host, self.port)
        self.conn.login(client_login_name=self.username, client_login_password=self.password)
        self.conn.use(sid=1)
        self.conn.send_keepalive()
        self.conn.servernotifyregister(event='textserver')
        while True:
            self.conn.send_keepalive()
            try:
                event = self.conn.wait_for_event(timeout=60)
                self.handle(event)
            except TS3TimeoutError:
                pass

    def handle(self, event: TS3Event):
        global cmd_alias
        parsed_event = event.parsed[0]
        sender_id = parsed_event['invokerid']
        # print(parsed_event)
        message: str = parsed_event['msg']
        alias = None
        for a in cmd_alias.keys():
            if message.startswith(a):
                alias = a
                break
        if not alias:
            return
        args = message.strip(alias).split(' ')
        try:
            func = self.__getattribute__(f"cmd_{cmd_alias[alias]}")
        except AttributeError:
            return
        func(*args)

    def send(self, msg: str, color: str = None):
        if color is None:
            self.conn.sendtextmessage(targetmode=3, target=1, msg=msg)
        else:
            self.conn.sendtextmessage(targetmode=3, target=1, msg=f"[color={color}]" + msg + "[/color]")

    def exec(self, *args):
        urlencoded_args = map(lambda x: urllib.parse.quote(x, safe=''), args)
        url = self.bot_api + "/api/bot/use/0/(/" + '/'.join(urlencoded_args)
        try:
            requests.get(url)
        except Exception:
            return False
        return True

    def cmd_play(self, *args):
        if args[0] == '':
            self.exec('play')
            return
        self.send("正在搜索中....")
        songs = self.api.search(args[0])
        suggestions = self.api.suggest(args[0])
        if songs == [] and suggestions:
            self.send(f"没有搜到{args[0]}哦，建议你搜搜[b]{'，'.join(suggestions)}[b]")
        elif songs:
            song = songs[0]
            link = self.api.get_song(song['ID'])
            avatar = self.api.get_avatar(song['ID'])
            singers = ' '.join(singer['name'] for singer in song['singers'])
            title = song['title']
            self.exec('play', link)
            self.exec('bot', 'description', 'set', f"！！正在播放来自{singers}的{title}")
            self.exec('bot', 'avatar', 'set', avatar)
            self.send(f"！！开始播放来自{singers}的{title}", color='green')
        else:
            self.send(f"网络错误或者没有找到你要的歌内QAQ。", color='red')
        return

    def cmd_search(self, *args):
        self.send("正在搜索中....")
        if len(args) == 2:
            songs = self.api.search(args[0], page_size=args[1])
        else:
            songs = self.api.search(args[0])
        suggestions = self.api.suggest(args[0])
        if songs == [] and suggestions:
            self.send(f"没有搜到{args[0]}哦，建议你搜搜[b]{'，'.join(suggestions)}[/b]")
        elif songs:
            infos = ["搜索到的结果如下内："]
            for song in songs:
                info_str = f"ID：{song['ID']}  歌名：{song['title']}  歌手：{' '.join(singer['name'] for singer in song['singers'])}"
                if not song['album']['ID'] == '0':
                    info_str += f"  专辑：{song['album']['name']}"
                infos.append(info_str)
            self.send("[b]" + '\n'.join(infos) + "[/b]")
        else:
            self.send(f"网络错误或者没有找到你要的歌内QAQ。", color='red')
        return

    def cmd_pause(self, *args):
        self.exec('pause')

    def cmd_help(self, *args):
        self.send()

    def cmd_help(self, *args):
        self.send("""[b][color=blue]食用方式[/color]
        
    想要听音乐请输入“[i]我要听[歌名][/i]”或者“[i]播放[歌名][/i]”，比如“[i]我要听APT[/i]”和“[i]播放APT[/i]”。

    想要搜索音乐请输入“[i]搜索[歌名][/i]”，比如“[i]搜索APT[/i]”。默认显示20条记录，如需显示更多请在后面加上数量，比如“[i]搜索APT 40[/i]”就会显示40条搜索结果。

    输入“[i]暂停[/i]”即可暂停。

    输入“[i]怎么玩[/i]”或“[i]帮助[/i]”即可获取帮助。[/b]""")

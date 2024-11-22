import urllib
from urllib.parse import urlencode

import requests
import ts3
from ts3.query import TS3Connection, TS3TimeoutError
from ts3.response import TS3Event

from Api import Api

cmd_alias = {"我要听": "play", "播放ID": "play_id" ,"播放": "play", "搜索": "search", "暂停": "pause", "怎么玩": "help", "帮助": "help", "聊天":"chat"}


class AudioBot:
    def __init__(self, username, password, uid, bot_api, api: Api, host, port=10011):
        self.uid = uid
        self.username = username
        self.password = password
        self.nickname = "mew~"
        self.host = host
        self.port = port
        self.api = api
        self.bot_api = bot_api
        self.chat_api = None
        self.conn: TS3Connection = None
        self.chat_enable=False
        self.ignore_users=['serveradmin']

    def listen(self):
        if self.conn is None:
            self.conn = ts3.query.TS3Connection(self.host, self.port)
        else:
            self.conn.close()
            self.conn = ts3.query.TS3Connection(self.host, self.port)
        self.conn.login(client_login_name=self.username, client_login_password=self.password)
        self.conn.use(sid=1)
        self.conn.clientupdate(client_nickname=self.nickname)
        self.conn.send_keepalive()
        self.conn.servernotifyregister(event='textserver')
        while True:
            self.conn.send_keepalive()
            try:
                event = self.conn.wait_for_event(timeout=60)
                self.handle(event)
            except TS3TimeoutError:
                if self.chat_enable:
                    self.chat_enable=False
                    self.send("那我先下线了喵~~")
                pass

    def handle(self, event: TS3Event):
        global cmd_alias
        parsed_event = event.parsed[0]
        sender_uid = parsed_event['invokeruid']
        if sender_uid in self.ignore_users:
            return
        sender_name = parsed_event['invokername']
        print(parsed_event)
        message: str = parsed_event['msg']
        alias = None
        for a in cmd_alias.keys():
            if message.startswith(a):
                alias = a
                break
        if not alias:
            if self.chat_enable:
                self.cmd_chat(sender_name,message)
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

        if songs is not None and len(songs) > 0:
            song = songs[0]
            self.play_song(song)
        else:
            if songs==[]:   # 如果结果为0个结果则触发suggest
                suggestions = self.api.suggest(args[0])
                if suggestions is not None and len(suggestions) > 0:    # 如果suggest结果为非空则发送建议
                    self.send(f"没有搜到{args[0]}哦，建议你搜搜[b]{'，'.join(suggestions)}[b]")
                    return
            self.send(f"网络错误或者没有找到你要的歌内QAQ。", color='red')  #当歌曲搜索结果为None 或者 当suggest搜索结果为None 或者 歌曲搜索结果和suggest结果均为空列表时
        return

    def cmd_play_id(self, *args):
        if args[0] == '':
            self.send("请跟上ID。")
            return
        info=self.api.get_info(args[0])
        if not info:
            self.send(f"网络错误或者没有找到你要的歌内QAQ。", color='red')
            return
        self.play_song(info[0])
        return



    def cmd_search(self, *args):
        if args[0] == '':
            return
        self.send("正在搜索中....")
        if len(args) == 2:
            songs = self.api.search(args[0], page_size=args[1])
        else:
            songs = self.api.search(args[0])

        if songs is not None and len(songs) > 0:
            infos = ["搜索到的结果如下内："]
            for song in songs:
                info_str = f"ID：{song['ID']}  歌名：{song['title']}  歌手：{' '.join(singer['name'] for singer in song['singers'])}"
                if not song['album']['ID'] == '0':
                    info_str += f"  专辑：{song['album']['name']}"
                infos.append(info_str)
            self.send("[b]" + '\n'.join(infos) + "[/b]")
        else:
            if songs == []:  # 如果结果为0个结果则触发suggest
                suggestions = self.api.suggest(args[0])
                if suggestions is not None and len(suggestions) > 0:  # 如果suggest结果为非空则发送建议
                    self.send(f"没有搜到{args[0]}哦，建议你搜搜[b]{'，'.join(suggestions)}[b]")
                    return
            self.send(f"网络错误或者没有找到你要的歌内QAQ。",
                      color='red')  # 当歌曲搜索结果为None 或者 当suggest搜索结果为None 或者 歌曲搜索结果和suggest结果均为空列表时
        return

    def cmd_pause(self, *args):
        self.exec('pause')

    def cmd_help(self, *args):
        self.send("""[b][color=blue]食用方式[/color]
        
    想要听音乐请输入“[i]我要听[歌名][/i]”或者“[i]播放[歌名][/i]”，比如“[i]我要听APT[/i]”和“[i]播放APT[/i]”。

    想要搜索音乐请输入“[i]搜索[歌名][/i]”，比如“[i]搜索APT[/i]”。默认显示20条记录，如需显示更多请在后面加上数量，比如“[i]搜索APT 40[/i]”就会显示40条搜索结果。

    输入“[i]暂停[/i]”即可暂停。
    
    输入“[i]聊天[/i]”即可和机器人开始聊天，超过一分钟未回复会自动下线。

    输入“[i]怎么玩[/i]”或“[i]帮助[/i]”即可获取帮助。[/b]""")

    def cmd_chat(self, *args):
        print(args)
        if self.chat_api is None:
            self.send("聊天api未设置。")
            return
        if args[0] == '':
            self.chat_enable=True
            self.chat_api.reset()
            self.send("聊天模式已开启喵~~")
            return
        if not self.chat_enable:
            return
        sender=args[0]
        msg=args[1]
        response=self.chat_api.chat(f"{sender}: {msg}")
        self.send(response)
        return

    def play_song(self, song:dict):
        try:
            link = self.api.get_song(song['ID'])
            avatar = self.api.get_avatar(song['ID'])
            singers = ' '.join(singer['name'] for singer in song['singers'])
            title = song['title']
            self.exec('play', link)
            self.exec('bot', 'description', 'set', f"！！正在播放来自{singers}的{title}")
            self.exec('bot', 'avatar', 'set', avatar)
            self.send(f"！！开始播放来自{singers}的{title}", color='green')
        except Exception:
            self.send("播放错误QAQ",color='red')
        return
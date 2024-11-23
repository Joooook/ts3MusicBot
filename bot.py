import concurrent.futures
import re
import threading
import time
import urllib
from urllib.parse import urlencode

import requests
import ts3
from ts3.query import TS3Connection, TS3TimeoutError
from ts3.response import TS3Event

from Api import Api
from NeteaseApi import NeteaseApi

# cmd_alias = {"我想听": "add", "我要听": "add", "跳转": "jump", "添加ID": "add_id", "添加": "add", "歌单": "info",
#              "下一首": "next", "上一首": "previous", "播放ID": "add_id", "播放歌单": "play_list", "播放": "add",
#              "搜索": "search", "暂停": "pause", "怎么玩": "help", "帮助": "help", "聊天": "chat"}
cmd_alias = [{'command': 'add_id', 'alias': ["添加ID", "播放ID"], 'help':'添加对应ID歌曲到当前歌单', 'examples':["添加ID123456", "播放ID789798"]},
             {'command': 'add', 'alias': ["我想听", "我要听"], 'help':'自动搜索歌曲并添加到当前歌单', 'examples':["我想听爱情转移", "我要听爱情转移"]},
             {'command': 'help', 'alias': ["帮助", "怎么玩"], 'help':'显示帮助手册', 'examples':["帮助", "怎么玩"]},
             {'command': 'chat', 'alias': ["聊天"], 'help':'喵~~', 'examples':["聊天"]},
             {'command': 'search', 'alias': ["搜索"], 'help':'搜索曲库歌曲', 'examples':["搜索爱情转移"]},
             {'command': 'pause', 'alias': ["暂停"], 'help':'暂停', 'examples':["暂停"]},
             {'command': 'jump', 'alias': ["跳转"], 'help':'跳转到第N首歌曲', 'examples':["跳转50"]},
             {'command': 'clear', 'alias': ["清空"], 'help':'清空当前歌单', 'examples':["清空"]},
             {'command': 'next', 'alias': ["下一首"], 'help':'下一首', 'examples':["下一首"]},
             {'command': 'previous', 'alias': ["上一首"], 'help':'上一首', 'examples':["上一首"]},
             {'command': 'info', 'alias': ["当前歌单", "歌单", "查看歌单"], 'help':'查看当前歌单或其他歌单', 'examples':["当前歌单", "歌单[歌单ID]","歌单123", "查看歌单789"]},
             {'command': 'list_list', 'alias': ["所有歌单"], 'help':'查看所有歌单', 'examples':["所有歌单"]},
             {'command': 'play_list', 'alias': ["播放歌单"], 'help':'播放对应歌单ID', 'examples':["播放歌单123"]},
             {'command': 'delete_list', 'alias': ["删除歌单"], 'help':'删除对应歌单ID', 'examples':["删除歌单13456"]},
             {'command': 'save_current_list', 'alias': ["保存歌单"], 'help':'保存当前播放歌单到新歌单', 'examples':["保存歌单"]},
            {'command': 'add', 'alias': ["播放", "添加"], 'help':'自动搜索歌曲并添加到当前歌单', 'examples':["播放Lemon", "添加Lemon"]},
             ]


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
        self.netease_api: NeteaseApi = None
        self.conn: TS3Connection = None
        self.chat_enable = False
        self.ignore_users = ['serveradmin','ServerQuery','kpixaDUvjkJFc7BPXm1ULo5JR2M=']
        self.executor=concurrent.futures.ThreadPoolExecutor(max_workers=2)
        self.threads=[]

    def wait_event(self, timeout: int = 10):
        while True:
            event = self.conn.wait_for_event(timeout=timeout)
            parsed_event = event.parsed[0]
            sender_uid = parsed_event['invokeruid']
            if sender_uid not in self.ignore_users:
                return event

    def run(self):
        if self.conn is None:
            self.conn = ts3.query.TS3Connection(self.host, self.port)
        else:
            self.conn.close()
            self.conn = ts3.query.TS3Connection(self.host, self.port)
        listen_thread = self.executor.submit(self.listen)
        update_thread = self.executor.submit(self.update)
        self.threads.clear()
        self.threads.append(listen_thread)
        self.threads.append(update_thread)

    def update(self):
        print("update thread started.")
        previous_link = None
        while True:
            time.sleep(1)
            rep=self.exec("song")
            if rep and rep.status_code == 200:
                link = rep.json()['Link']
                if previous_link != link:
                    song_id = re.findall(r'ID=(\d+)&', link)[0]
                    song = self.api.get_info(song_id)[0]
                    self.update_bot(song)
                    previous_link = link

    def listen(self):
        if self.conn is None:
            return
        print("listen thread started.")
        self.conn.login(client_login_name=self.username, client_login_password=self.password)
        self.conn.use(sid=1)
        self.conn.clientupdate(client_nickname=self.nickname)
        self.conn.send_keepalive()
        self.conn.servernotifyregister(event='textserver')
        while True:
            self.conn.send_keepalive()
            try:
                event = self.wait_event(timeout=60)
                self.handle(event)
            except TS3TimeoutError:
                self.timeout()
                pass

    def timeout(self):
        if self.chat_enable:
            self.chat_enable = False
            self.send("那我先下线了喵~~")
        return

    def handle(self, event: TS3Event):
        global cmd_alias
        parsed_event = event.parsed[0]
        sender_name = parsed_event['invokername']
        sender_uid = parsed_event['invokeruid']
        message: str = parsed_event['msg']
        print(parsed_event)
        command = None
        alias = None
        for i in cmd_alias:
            for a in i['alias']:
                if message.startswith(a):
                    command = i['command']
                    alias = a
                    break
            if command is not None:
                break
        if command is None and not self.chat_enable:
            return
        elif command is None and self.chat_enable:
            self.cmd_chat(sender_name, message)
            return
        else:
            args = message.strip(alias).strip().split(' ')
            try:
                func = self.__getattribute__(f"cmd_{command}")
            except AttributeError:
                return
            func(sender_uid,*args)
            return

    def send(self, msg: str, color: str = None):
        targetmode = 3
        target = 1
        # targetmode=2
        # target = 0
        if color is None:
            self.conn.sendtextmessage(targetmode=targetmode, target=target, msg=msg)
        else:
            self.conn.sendtextmessage(targetmode=targetmode, target=target, msg=f"[color={color}]" + msg + "[/color]")

    def exec(self, *args):
        urlencoded_args = map(lambda x: urllib.parse.quote(x, encoding='UTF-8', safe=''), args)
        url = self.bot_api + "/api/bot/use/0/(/" + '/'.join(urlencoded_args)
        try:
            rep = requests.get(url)
        except Exception:
            return None
        return rep

    def update_bot(self, song: dict):
        title = song['title']
        avatar = self.api.get_avatar(song['ID'])
        singers = ' '.join(singer['name'] for singer in song['singers'])
        self.exec('bot', 'description', 'set', f"！！正在播放来自{singers}的{title}")
        self.exec('bot', 'avatar', 'set', avatar)

    def play_song(self, song: dict):
        try:
            link = self.api.get_song(song['ID'])
            singers = ' '.join(singer['name'] for singer in song['singers'])
            title = song['title']
            self.exec('play', link)
            self.update_bot(song)
            self.send(f"！！开始播放来自{singers}的{title}", color='green')
        except Exception:
            self.send("播放错误QAQ", color='red')
        return

    def add_song(self, song: dict):
        try:
            link = self.api.get_song(song['ID'])
            avatar = self.api.get_avatar(song['ID'])
            singers = ' '.join(singer['name'] for singer in song['singers'])
            title = song['title']
            self.exec('add', link)
            self.send(f"！！下一首将播放来自{singers}的{title}", color='green')
        except Exception:
            self.send("播放错误QAQ", color='red')
        return

    def get_list_songs_info(self, list_id: str = None):
        if list_id is None:
            command = ['info']
        else:
            command = ['list', 'show', list_id]
        data = {'Items': []}
        offset = 0
        while True:
            rep = self.exec(*(command + [str(offset), '20']))
            if not rep:
                return None
            if list_id is None:
                data['PlaybackIndex'] = rep.json()['PlaybackIndex']
            data['Items'] += rep.json()['Items']
            data['SongCount'] = rep.json()['SongCount']
            data['Title'] = rep.json()['Title']
            offset += 20
            if len(data['Items']) >= data['SongCount']:
                break
        return data

    def cmd_play(self,sender_uid, *args):
        if args[0] == '':
            self.exec('play')
            return
        self.send("正在搜索中....")
        songs = self.api.search(args[0])
        if songs is not None and len(songs) > 0:
            song = songs[0]
            self.play_song(song)
        else:
            if songs == []:  # 如果结果为0个结果则触发suggest
                suggestions = self.api.suggest(args[0])
                if suggestions is not None and len(suggestions) > 0:  # 如果suggest结果为非空则发送建议
                    self.send(f"没有搜到{args[0]}哦，建议你搜搜[b]{'，'.join(suggestions)}[b]")
                    return
            self.send(f"网络错误或者没有找到你要的歌内QAQ。",
                      color='red')  # 当歌曲搜索结果为None 或者 当suggest搜索结果为None 或者 歌曲搜索结果和suggest结果均为空列表时
        return

    def cmd_play_id(self,sender_uid, *args):
        if args[0] == '':
            self.send("请跟上ID。")
            return
        self.send("正在搜索中....")
        song_id = re.sub(r'\D', '', args[0])
        info = self.api.get_info(song_id)
        if not info:
            self.send(f"网络错误或者没有找到你要的歌内QAQ。", color='red')
            return
        self.play_song(info[0])
        return

    def cmd_add_id(self,sender_uid, *args):
        if args[0] == '':
            self.send("请跟上ID。")
            return
        self.send("正在搜索中....")
        keys: str = args[0]
        keys = keys.replace(',', '|').replace('，', '|')
        print(keys)
        for key in keys.split('|'):
            song_id = re.sub(r'\D', '', key)
            info = self.api.get_info(song_id)
            if not info:
                self.send(f"网络错误或者没有找到你要的歌内QAQ。", color='red')
                continue
            self.add_song(info[0])
        return

    def cmd_search(self,sender_uid, *args):
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

    def cmd_pause(self,sender_uid, *args):
        self.exec('pause')

    def cmd_info(self,sender_uid, *args):
        if args[0] == '':
            list_id = "当前"
            data = self.get_list_songs_info()
        else:
            list_id = args[0]
            data = self.get_list_songs_info(list_id)
        if not data:
            self.send("未找到歌单ID或网络错误请重试...", color='red')
            return
        if list_id == "当前":
            now_id = data['PlaybackIndex']
        else:
            now_id = -1
        items = data['Items']
        song_count = data['SongCount']
        id_list = []
        for song in items:
            song_id = re.findall(r'ID=(\d+)&', song['Link'])[0]
            id_list.append(song_id)
        if not id_list:
            self.send(f"[b]{list_id}歌单为空喵~[/b]", color='blue')
            return
        list_songs_info = self.api.get_info(','.join(id_list))
        if list_songs_info is None:
            self.send("出错了请重试...", color='red')
            return
        song_list_str = f"[b][color=blue]{list_id}歌单 共{song_count}首歌[/color]\n"
        for index, song in enumerate(list_songs_info):
            song_info_str = f"[{str(index + 1).zfill(len(str(song_count)))}]  ID：{song['ID'].ljust(9, '-')}  {song['title']}  {'，'.join(singer['name'] for singer in song['singers'])}"
            if index == now_id:
                song_info_str = "[color=green]" + song_info_str + " <==正在播放 [/color]"
            song_list_str += song_info_str + '\n'
        self.send(song_list_str)
        return

    def cmd_next(self,sender_uid, *args):
        self.exec('next')

    def cmd_previous(self,sender_uid, *args):
        self.exec('previous')

    def cmd_help(self,sender_uid, *args):
        global cmd_alias
        help_str='[b][color=blue]食用方式[/color]\n'
        for command in cmd_alias:
            help_str += f"{command['help']}   功能：{command['command']}  指令：[color=green]{'，'.join(command['alias'])}[/color]  例子：{'，'.join(command['examples'])}\n"
        self.send(help_str)

    def cmd_chat(self,sender_uid, *args):
        if self.chat_api is None:
            self.send("聊天api未设置。")
            return
        if args[0] == '':
            self.chat_enable = True
            self.chat_api.reset()
            self.send("聊天模式已开启喵~~")
            return
        if not self.chat_enable:
            return
        if len(args) < 2:
            return
        sender = args[0]
        msg = args[1]
        response = self.chat_api.chat(f"{sender}：{msg}")
        self.send(response)
        return

    def cmd_add(self,sender_uid, *args):
        if args[0] == '':
            self.exec('play')
            return
        self.send("正在搜索中....")
        keys: str = args[0]
        keys = keys.replace(',', '|').replace('，', '|')
        for key in keys.split('|'):
            songs = self.api.search(key)
            if songs is not None and len(songs) > 0:
                song = songs[0]
                self.add_song(song)
            else:
                if songs == []:  # 如果结果为0个结果则触发suggest
                    suggestions = self.api.suggest(args[0])
                    if suggestions is not None and len(suggestions) > 0:  # 如果suggest结果为非空则发送建议
                        self.send(f"没有搜到{args[0]}哦，建议你搜搜[b]{'，'.join(suggestions)}[b]")
                        continue
                self.send(f"网络错误或者没有找到你要的歌内QAQ。",
                          color='red')  # 当歌曲搜索结果为None 或者 当suggest搜索结果为None 或者 歌曲搜索结果和suggest结果均为空列表时
        return

    def cmd_jump(self,sender_uid, *args):
        if args[0] == '':
            return
        try:
            index = int(args[0]) - 1
        except ValueError:
            self.send("？跳转[索引]")
            return
        rep = self.exec('info')
        if not rep:
            self.send("出错了...", color='red')
        song_count = rep.json()['SongCount']
        if index < 0 or index >= song_count:
            self.send("超出了QAQ...", color='red')
            return
        self.exec('jump', str(index))
        self.send(f"！！成功跳转到第{str(index + 1)}首歌", color='green')
        return

    def cmd_clear(self,sender_uid, *args):
        self.send("你确定要清空当前歌单吗？[是/否]")
        try:
            event = self.wait_event(timeout=5)
        except TS3TimeoutError:
            self.send("未执行操作。")
            return
        parsed_event = event.parsed[0]
        message: str = parsed_event['msg']
        if message.startswith("是"):
            self.exec('clear')
            self.send("已为您清空歌单。")
        else:
            self.send("好的呢~")
        return

    def cmd_play_list(self,sender_uid, *args):
        if args[0] == '':
            self.send("请输入歌单ID。")
            return
        rep = self.exec("list", "play", args[0])
        if not rep:
            self.send("网络错误请重试QAQ", color='red')
            return
        if rep.status_code == 204:
            self.send(f"！！开始播放歌单ID：{args[0]}",color='green')
        else:
            self.send(f"未找到歌单QAQ。",color='red')
        return

    def cmd_delete_list(self,sender_uid, *args):
        if args[0] == '':
            self.send("请输入歌单ID。")
            return
        self.send("你确定要删除该歌单吗？[是/否]")
        try:
            event = self.wait_event(timeout=5)
        except TS3TimeoutError:
            self.send("未执行操作。")
            return
        parsed_event = event.parsed[0]
        message: str = parsed_event['msg']
        if message.startswith("是"):
            self.exec('list','delete', args[0])
            self.send("已为您删除歌单。")
        else:
            self.send("好的呢~")
        return

    def cmd_list_list(self,sender_uid, *args):
        rep = self.exec('list', 'list')
        if rep is None:
            self.send("没有找到歌单或者网络错误QAQ", color='red')
            return
        lists = rep.json()
        lists_info_str = "[b][color=blue]所有歌单[/color][/b]\n"
        for l in lists:
            lists_info_str += f"[b]ID：{l['Id']}\t歌单名：{l['Title']}\t歌曲数量：{l['SongCount']}[/b]\n"
        self.send(lists_info_str)
        return

    def cmd_save_current_list(self,sender_uid, *args):
        self.send("请输入要保存为的歌单名：")
        try:
            event = self.wait_event(timeout=10)
        except TS3TimeoutError:
            self.send("未执行操作。")
            return
        parsed_event = event.parsed[0]
        message: str = parsed_event['msg']

        rep = self.exec('list', 'list')
        if rep is None:
            self.send("没有找到歌单或者网络错误QAQ", color='red')
            return
        lists = rep.json()
        list_ids = [l['Id'] for l in lists]
        new_list_name = message
        new_list_id = new_list_name
        index = 1
        while True:
            if new_list_id not in list_ids:
                break
            new_list_id = new_list_name + f'({index})'
            index += 1
        self.exec('list', "create", new_list_id, new_list_name)  # 可以改为新建歌单
        data = self.get_list_songs_info()
        if not data:
            self.send("出错了请重试...", color='red')
        song_count = data['SongCount']
        data = self.get_list_songs_info(song_count)
        if not data:
            self.send("出错了请重试...", color='red')
        items = data['Items']
        for item in items:
            self.exec('list', 'add', str(new_list_id), item['Link'])
            self.send(f"{item['Title']}成功导入。")
        self.send(f"成功导入歌曲到歌单ID：{new_list_id}  歌单名：{message}。")
        self.cmd_list_list()
        return

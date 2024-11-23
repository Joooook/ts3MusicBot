import concurrent.futures
import re
import threading
import time
import urllib
from urllib.parse import urlencode

import requests
import ts3
from openai import audio
from ts3.query import TS3Connection, TS3TimeoutError
from ts3.response import TS3Event

from Api import Api
from NeteaseApi import NeteaseApi
from Pet import PetApi, PetInfo
from data_structures.Sender import Sender

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
            {'command': 'pet_new', 'alias': ["创建宠物", "新建宠物"], 'help':'新建一只宠物。', 'examples':["创建宠物", "新建宠物"]},
            {'command': 'pet_upgrade', 'alias': ["升级","宠物升级"], 'help':'宠物升级。', 'examples':["升级","宠物升级"]},
            {'command': 'pet_show', 'alias': ["宠物", "我的宠物","查看宠物"], 'help':'查看宠物信息。', 'examples':["宠物", "我的宠物","查看宠物"]},
            {'command': 'pet_delete', 'alias': ["删除宠物", "抛弃宠物"], 'help':'删除宠物。', 'examples':["删除宠物", "抛弃宠物"]},
            {'command': 'pet_feed', 'alias': ["喂食", "喂食宠物","喂宠物"], 'help':'喂宠物。', 'examples':["喂食", "喂食宠物","喂宠物"]},
            {'command': 'checkin', 'alias': ["签到"], 'help':'签到。', 'examples':["签到"]}
             ]


class AudioBot:
    def __init__(self, username, password, audio_bot_uid:str, bot_api, api: Api, host, port=10011):
        self.audio_bot_uid = audio_bot_uid
        self.username = username
        self.password = password
        self.nickname = "mew~"
        self.host = host
        self.port = port
        self.api = api
        self.bot_api = bot_api
        self.chat_api = None
        self.pet_api:PetApi = None
        self.netease_api: NeteaseApi = None
        self.conn: TS3Connection = None
        self.chat_enable = False
        self.ignore_users = ['serveradmin','ServerQuery','kpixaDUvjkJFc7BPXm1ULo5JR2M=']
        self.sid=1
        self.cid=1
        self.targetmode = 3 #消息发送模式
        self.timeout = 60 # 超时处理阈值，实际上这里是listen的轮数，所以和实际60秒有差别。
        self.interval = 1 # listen间隔
        self.previous_link = None

    def wait_event(self, timeout: int = 10):
        while True:
            event = self.conn.wait_for_event(timeout=timeout)
            parsed_event = event.parsed[0]
            sender_uid = parsed_event['invokeruid']
            if sender_uid not in self.ignore_users:
                return event

    def connect(self):
        if self.conn is None:
            self.conn = ts3.query.TS3Connection(self.host, self.port)
        else:
            self.conn.close()
            self.conn = ts3.query.TS3Connection(self.host, self.port)
        self.conn.login(client_login_name=self.username, client_login_password=self.password)
        self.conn.use(sid=1)
        self.conn.clientupdate(client_nickname=self.nickname)
        self.conn.send_keepalive()
        return

    def run(self):
        self.connect()
        self.listen()

    def listen(self):
        if self.conn is None:
            return
        print("listen started.")
        self.conn.servernotifyregister(event='textserver')
        self.conn.servernotifyregister(event='textchannel')
        count = 0
        while True:
            self.conn.send_keepalive()
            try:
                self.update()
                self.follow()
                event = self.wait_event(timeout=self.interval)
                self.handle(event)
            except Exception:
                pass
            count+=1
            if count > self.timeout:
                count = 0
                self._timeout()

    def follow(self):
        """
        为了接收到和音乐机器人同一频道下的消息，需要跟随音乐机器人移动
        :return:
        """
        res = self.conn.clientgetids(cluid=self.audio_bot_uid)
        if not res:
            raise Exception('AudioBot Not Found.')
        audio_bot_clid = res[0]['clid']
        audio_bot_cid = self.conn.clientinfo(clid=audio_bot_clid)[0]['cid']
        res = self.conn.whoami()
        bot_clid = res[0]['client_id']
        bot_cid = res[0]['client_channel_id']
        self.cid = bot_cid
        if bot_cid != audio_bot_cid:
            self.conn.clientmove(cid=audio_bot_cid,clid=bot_clid)
        return

    def update(self):
        """用于更新AudioBot的歌曲信息"""
        rep = self.exec("song")
        if rep and rep.status_code == 200:
            link = rep.json()['Link']
            if self.previous_link != link:
                song_id = re.findall(r'ID=(\d+)&', link)[0]
                song = self.api.get_info(song_id)[0]
                title = song['title']
                avatar = self.api.get_avatar(song['ID'])
                singers = ' '.join(singer['name'] for singer in song['singers'])
                self.exec('bot', 'description', 'set', f"！！正在播放来自{singers}的{title}")
                self.exec('bot', 'avatar', 'set', avatar)
                self.previous_link = link

    def _timeout(self):
        if self.chat_enable:
            self.chat_enable = False
            self.send("那我先下线了喵~~")
        return

    def handle(self, event: TS3Event):
        global cmd_alias
        parsed_event = event.parsed[0]
        sender_name = parsed_event['invokername']
        sender_uid = parsed_event['invokeruid']
        self.targetmode = parsed_event['targetmode']
        sender = Sender(sender_name=sender_name, sender_uid=sender_uid)
        message: str = parsed_event['msg']
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
            self.cmd_chat(sender, message)
            return
        else:
            args = message.strip(alias).strip().split(' ')
            try:
                func = self.__getattribute__(f"cmd_{command}")
            except AttributeError:
                return
            func(sender,*args)
            return

    def send(self, msg: str, color: str = None):
        if int(self.targetmode) == 3:
            target = self.sid
        else:
            target = self.cid
        if color is None:
            self.conn.sendtextmessage(targetmode=self.targetmode, target=target, msg=msg)
        else:
            self.conn.sendtextmessage(targetmode=self.targetmode, target=target, msg=f"[color={color}]" + msg + "[/color]")

    def exec(self, *args):
        urlencoded_args = map(lambda x: urllib.parse.quote(x, encoding='UTF-8', safe=''), args)
        url = self.bot_api + "/api/bot/use/0/(/" + '/'.join(urlencoded_args)
        try:
            rep = requests.get(url)
        except Exception:
            return None
        return rep

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

    def cmd_play(self,sender, *args):
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

    def cmd_play_id(self,sender, *args):
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

    def cmd_add_id(self,sender, *args):
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

    def cmd_search(self,sender, *args):
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

    def cmd_pause(self,sender, *args):
        self.exec('pause')

    def cmd_info(self,sender, *args):
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

    def cmd_next(self,sender, *args):
        self.exec('next')

    def cmd_previous(self,sender, *args):
        self.exec('previous')

    def cmd_help(self,sender, *args):
        global cmd_alias
        help_str='[b][color=blue]食用方式[/color]\n'
        for command in cmd_alias:
            help_str += f"{command['help']}   功能：{command['command']}  指令：[color=green]{'，'.join(command['alias'])}[/color]  例子：{'，'.join(command['examples'])}\n"
        self.send(help_str)

    def cmd_chat(self,sender, *args):
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
        msg = args[0]
        response = self.chat_api.chat(f"{sender.sender_name}：{msg}")
        self.send(response)
        return

    def cmd_add(self,sender, *args):
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

    def cmd_jump(self,sender, *args):
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

    def cmd_clear(self,sender, *args):
        res= self.confirm("你确定要清空当前歌单吗？")
        if res:
            self.exec('clear')
            self.send("已为您清空歌单。")
        else:
            self.send("好的呢~")
        return

    def cmd_play_list(self,sender, *args):
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

    def cmd_delete_list(self,sender, *args):
        if args[0] == '':
            self.send("请输入歌单ID。")
            return
        res = self.confirm("你确定要删除该歌单吗？")
        if res:
            self.exec('list','delete', args[0])
            self.send("已为您删除歌单。")
        else:
            self.send("好的呢~")
        return

    def cmd_list_list(self,sender, *args):
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

    def cmd_save_current_list(self,sender, *args):
        message: str = self.ask("请输入要保存为的歌单名")
        if not message:
            return
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

    def cmd_pet_new(self,sender, *args):
        if not self.check_pet_api():
            return
        if self.pet_api.have_pet(sender.sender_uid):
            res=self.confirm("每个人只能创建一只宠物哦，是否要覆盖掉当前宠物？")
            if not res:
                self.send("好的呢")
                return
        msg = self.ask("请输入宠物描述（15秒内）",timeout=15)
        if not msg:
            return
        self.send("生成中....")
        pet_info : PetInfo = self.pet_api.new_pet(sender.sender_uid,msg)
        if not pet_info:
            self.send("创建宠物失败，请重试。",color='red')
            return
        self.send(f"创建宠物成功！恭喜{sender.sender_name}拥有了一只{pet_info.name}。")

    def cmd_pet_upgrade(self,sender, *args):
        if not self.check_pet_api():
            return
        if not self.pet_api.have_pet(sender.sender_uid):
            self.send("你还没有宠物呢。")
            return
        if not self.pet_api.upgradable(sender.sender_uid):
            self.send("你的宠物目前还不能升级呢。")
            return
        msg = self.ask("请输入技能描述（15秒内）",timeout=15)
        if not msg:
            return
        self.send("生成技能中....")
        skill = self.pet_api.upgrade_pet(sender.sender_uid,msg)
        if not skill:
            self.send("升级宠物失败，请重试。",color='red')
            return
        self.send(f"升级宠物成功！恭喜{sender.sender_name}的宠物获得了新技能{skill.name}。")

    def cmd_pet_list(self,sender, *args):
        if not self.check_pet_api():
            return

    def cmd_pet_feed(self,sender, *args):
        if not self.check_pet_api():
            return
        if not self.pet_api.have_pet(sender.sender_uid):
            self.send("你还没有宠物呢。")
            return
        res,reason = self.pet_api.feed_pet(sender.sender_uid)
        if reason=="NoFood":
            self.send("喂食失败！没有足够的食物。",color='red')
        elif reason=="Full":
            self.send("喂食失败！宠物还饱呢。",color='red')
        elif reason == "LevelUp":
            self.send("喂食成功！宠物升级！！！！！", color='green')
        elif reason == "Success":
            self.send("喂食成功！", color='green')

    def cmd_pet_show(self,sender, *args):
        if not self.check_pet_api():
            return
        if not self.pet_api.have_pet(sender.sender_uid):
            self.send("你还没有宠物呢。")
            return
        pet_info = self.pet_api.show_pet(sender.sender_uid)
        if pet_info is None:
            self.send("您还没拥有任何宠物呢。",color='red')
        skills_str='\n'.join([f'- 技能名称：{skill.name}  技能种类：{skill.type} 技能强度：{skill.capability}  技能描述：{skill.description}' for skill in pet_info.skills])
        self.send(f"""[b][color=blue]宠物信息如下：[/color]
宠物主人：{sender.sender_name}
宠物姓名：{pet_info.name}
等级：{pet_info.level}
身高：{pet_info.height}
体重：{pet_info.weight}
种族：{pet_info.species}
生命值：{pet_info.health}
剩余升级次数：{pet_info.upgrade_times}
库存食物：{pet_info.food_amount}
上次喂食：{pet_info.last_feed.strftime("%Y-%m-%d %H:%M")}
描述：{pet_info.description}
技能列表：
{skills_str}
""")

    def cmd_pet_delete(self,sender, *args):
        if not self.check_pet_api():
            return
        if not self.pet_api.have_pet(sender.sender_uid):
            self.send("你还没有宠物呢。")
            return
        confirm=self.confirm("你确定要删除你的宠物吗？")
        if not confirm:
            self.send("好的呢")
            return
        self.pet_api.delete_pet(sender.sender_uid)
        self.send("删除成功。",color='green')
        return

    def cmd_checkin(self,sender, *args):
        if not self.check_pet_api():
            return
        if not self.pet_api.have_pet(sender.sender_uid):
            self.send("你还没有宠物呢。")
            return
        self.pet_api.add_food_pet(sender.sender_uid)
        self.send("签到成功，获得1食物。")
        return

    def check_pet_api(self):
        if self.pet_api is None:
            self.send("宠物api未设置。")
            return False
        return True

    def confirm(self, question:str, timeout:int=5) -> bool:
        self.send(question+" [是/否]")
        try:
            event = self.wait_event(timeout=timeout)
        except TS3TimeoutError:
            self.send("未执行操作。")
            return False
        parsed_event = event.parsed[0]
        message: str = parsed_event['msg']
        if message.startswith("是"):
            return True
        return False

    def ask(self, question:str, timeout:int=10) -> str:
        self.send(question+" >")
        try:
            event = self.wait_event(timeout=timeout)
        except TS3TimeoutError:
            self.send("未执行操作。")
            return ''
        parsed_event = event.parsed[0]
        message: str = parsed_event['msg']
        return message.strip()
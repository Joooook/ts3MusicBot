import re
import time
import traceback
from typing import Union,List,Dict

import ts3
from ts3.query import TS3Connection, TS3TimeoutError
from ts3.response import TS3Event

from apis.audioBotApi.AudioBotApi import AudioBotApi
from apis.chatApi.ChatApi import ChatApi
from apis.muiscApi.MusicApi import MusicApi
from apis.muiscApi.data import Song, PlayList
from apis.neteaseApi.NeteaseApi import NeteaseApi
from apis.petApi.Pet import PetInfo
from apis.petApi.PetApi import PetApi, BattleResult
from apis.ttsApi.TTSApi import TTSApi
from data_structures.Command import Command
from data_structures.Sender import Sender
from utils.logger import init_logger

my_commands = [{'command': 'play_id', 'alias': ["播放ID"], 'help': '添加对应ID歌曲到当前歌单并播放',
              'examples': ["播放ID789798"]},
             {'command': 'add_id', 'alias': ["添加ID"], 'help': '添加对应ID歌曲到当前歌单',
              'examples': ["添加ID123456"]},
             {'command': 'play', 'alias': ["我想听", "我要听"], 'help': '自动搜索歌曲并添加到当前歌单',
              'examples': ["我想听爱情转移", "我要听爱情转移"]},
             {'command': 'help', 'alias': ["帮助", "怎么玩"], 'help': '显示帮助手册'},
             {'command': 'chat', 'alias': ["聊天"], 'help': '喵~~'},
             {'command': 'search', 'alias': ["搜索"], 'help': '搜索曲库歌曲', 'examples': ["搜索爱情转移"]},
             {'command': 'pause', 'alias': ["暂停"], 'help': '暂停'},
             {'command': 'jump', 'alias': ["跳转"], 'help': '跳转到第N首歌曲', 'examples': ["跳转50"]},
             {'command': 'volume', 'alias': ["音量"], 'help': '调节音量。', 'examples': ["音量50"]},
             {'command': 'clear', 'alias': ["清空"], 'help': '清空当前歌单'},
             {'command': 'next', 'alias': ["下一首"], 'help': '下一首'},
             {'command': 'previous', 'alias': ["上一首"], 'help': '上一首'},
             {'command': 'remove_item_list', 'alias': ["删除歌曲", "歌单删除"], 'help': '删除对应歌单ID的第x首歌',
              'examples': ["歌单删除1 12"]},
             {'command': 'add_item_list', 'alias': ["歌单添加"], 'help': '给对应歌单ID添加歌曲',
              'examples': ["歌单添加0 爱情转移，天天"]},
             {'command': 'add_id_item_list', 'alias': ["歌单添加ID"], 'help': '给对应歌单ID添加歌曲ID',
              'examples': ["歌单添加0 11321,3213213"]},
             {'command': 'show_list', 'alias': ["当前歌单", "歌单", "查看歌单"], 'help': '查看当前歌单或其他歌单',
              'examples': ["当前歌单", "歌单[歌单ID]", "歌单123", "查看歌单789"]},
             {'command': 'list_list', 'alias': ["所有歌单"], 'help': '查看所有歌单'},
             {'command': 'play_list', 'alias': ["播放歌单"], 'help': '播放对应歌单ID', 'examples': ["播放歌单123"]},
             {'command': 'delete_list', 'alias': ["删除歌单"], 'help': '删除对应歌单ID', 'examples': ["删除歌单13456"]},
             {'command': 'save_current_list', 'alias': ["保存歌单"], 'help': '保存当前播放歌单到新歌单'},
             {'command': 'add', 'alias': ["添加"], 'help': '自动搜索歌曲并添加到当前歌单',
              'examples': ["添加Lemon"]},
             {'command': 'play', 'alias': ["播放"], 'help': '自动搜索歌曲并插入到当前歌单并播放',
              'examples': ["播放Lemon"]},
             {'command': 'remove_item_current', 'alias': ["删除"], 'help': '删除当前的第x首歌',
              'examples': ["删除 12"]},
             {'command': 'pet_new', 'alias': ["创建宠物", "新建宠物"], 'help': '新建一只宠物。',
              'examples': ["创建宠物", "新建宠物"]},
             {'command': 'pet_upgrade', 'alias': ["升级", "宠物升级"], 'help': '宠物升级。'},
             {'command': 'pet_show', 'alias': ["宠物", "我的宠物", "查看宠物"], 'help': '查看宠物信息。'},
             {'command': 'pet_delete', 'alias': ["删除宠物", "抛弃宠物"], 'help': '删除宠物。'},
             {'command': 'pet_feed', 'alias': ["喂食", "喂食宠物", "喂宠物"], 'help': '喂宠物。',
              'examples': ["喂食", "喂食宠物", "喂宠物"]},
             {'command': 'pet_battle_add', 'alias': ["加入战斗"], 'help': '宠物加入战斗。'},
             {'command': 'pet_battle_list', 'alias': ["查看战斗", "战斗"], 'help': '宠物战斗。'},
             {'command': 'pet_battle_start', 'alias': ["开始战斗"], 'help': '宠物开始战斗。'},
             {'command': 'checkin', 'alias': ["签到"], 'help': '签到。'},
             {'command': 'broadcast', 'alias': ["广播"], 'help': '广播。', 'examples': ["广播你好"]},
             {'command': 'update_apis', 'alias': ["刷新接口"], 'help': '刷新接口状态。'},
             {'command': 'show_apis', 'alias': ["接口"], 'help': '查看接口状态。'},
             {'command': 'set_priority', 'alias': ["修改接口"], 'help': '修改接口优先级。',
              'examples': ["修改接口 default 50"]}
             ]


class TS3Bot:
    def __init__(self, username, password, bot_api, host, port=10011, nickname="mew~", api: MusicApi = None):
        self.username = username
        self.password = password
        self.nickname = nickname
        self.host = host
        self.port = port
        self.music_api = api
        # music_apis用于多api管理。
        self.music_apis: dict = {}
        self.current_music_api = 0
        self.bot_api = bot_api
        self.audio_bot_api = AudioBotApi(bot_api)
        response = self.audio_bot_api.get_uid()
        if response.succeed:
            self.audio_bot_uid = response.data
        else:
            raise Exception("AudioBot initialize failed.")
        self.chat_api: Union[ChatApi, None] = None
        self.pet_api: Union[PetApi, None] = None
        self.netease_api: Union[NeteaseApi, None] = None
        self.tts_api: Union[TTSApi, None] = None
        self.conn: Union[TS3Connection, None] = None
        self.chat_enable = False
        self.ignore_users = ['serveradmin', 'ServerQuery', self.audio_bot_uid]
        self.sid = 1  # server id
        self.cid = 1  # channel id
        self.targetmode = 3  # 消息发送模式
        self.interval = 3  # listen间隔不要过短，过短会导致跳歌等情况
        self.timeout = 60 # 超时处理阈值，不一定是严格60秒。
        self.previous_link = None
        self.prefix = "cmd_"
        self.hello = "Bot已上线。"
        self.logger = init_logger("TS3Bot")
        self.commands:List[Command] = []

    def wait_event(self, timeout: int = 10):
        """ 等待事件 """
        while True:
            event = self.conn.wait_for_event(timeout=timeout)
            try:
                parsed_event = event.parsed[0]
                sender_uid = parsed_event['invokeruid']
                if sender_uid not in self.ignore_users:
                    return event
            except KeyError as e:
                pass

    def connect(self):
        self.logger.info("Server query connecting...")
        # 连接并做初始设置。
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
        self.conn.servernotifyregister(event='textchannel')
        self.logger.info("Broadcast hello message.")
        self.conn.gm(msg=self.hello)
        self.audio_bot_api.clear() # 是否需要上线清空歌单
        return

    def run(self):
        if self.music_api:
            self.register_music_api(self.music_api, "default")
        self.connect()
        self.logger.info('Connected.')
        self.update_music_api()
        self.logger.info('Updated music api.')
        self.listen()

    def register_music_api(self, music_api: MusicApi, api_id: str, priority: int = 100):
        api_info = {"api": music_api, "id": api_id, "priority": priority, "accessibility": False}
        self.music_apis[api_id] = api_info
        self.logger.info(f"Register music api id: {api_id} priority: {priority}")

    def register_commands(self,commands:Union[List[Dict],Dict,Command,List[Command]]):
        if isinstance(commands,dict) or isinstance(commands,Command):
            _commands = [commands]
        else:
            _commands = commands
        for cmd in _commands:
            if isinstance(cmd,dict):
                self.commands.append(Command(**cmd))
            if isinstance(cmd, Command):
                self.commands.append(cmd)
        return

    def check_apis_access(self):
        for api_id, api_info in self.music_apis.items():
            api: MusicApi = api_info['api']
            response = api.available()
            if not response.succeed:
                self.music_apis[api_id]['accessibility'] = False
            else:
                self.music_apis[api_id]['accessibility'] = True
        return

    def update_music_api(self):
        self.check_apis_access()
        sorted_music_apis = sorted(self.music_apis.items(), key=lambda x: x[1]['priority'], reverse=True)
        for api_id, api_info in sorted_music_apis:
            if api_info['accessibility']:
                if self.current_music_api != api_id:
                    self.logger.info(f"Api switched to id: {api_id}.")
                    self.music_api = api_info['api']
                    self.current_music_api = api_id
                break
        return

    def listen(self):
        if self.conn is None:
            return
        time_start = time.time()
        self.logger.info("Start listening.")
        while True:
            self.conn.send_keepalive()
            try:
                self.follow()
                event = self.wait_event(timeout=self.interval)
                time_start = time.time()  # 一旦有消息则重置
                self.handle(event)
            except TS3TimeoutError:
                # update容易和handle冲突，比如当某首歌跳转之后但还没切换过来（因为AudioBot有一定的延迟），但是碰到update发现Bot处于未播放，于是切成下一首导致跳歌。所以把update安排在这，保证update调用之间一定有空隙。
                self.update()
            except Exception as e:
                self.logger.error("Listen error: ", traceback.format_exc())
                pass
            if time.time() - time_start > self.timeout:  # 长时间空闲处理逻辑
                time_start = time.time()
                self.standby()

    def follow(self):
        """
        为了接收到和音乐机器人同一频道下的消息，需要跟随音乐机器人移动
        :return:
        """
        res = self.conn.clientgetids(cluid=self.audio_bot_uid)
        if not res[0]:
            raise Exception('AudioBotNotFound.')
        response = self.audio_bot_api.get_cid()
        if not response.succeed:
            return
        audio_bot_cid = response.data
        try:
            res = self.conn.whoami()
            bot_clid = res[0]['client_id']
            bot_cid = res[0]['client_channel_id']
        except Exception:
            return
        self.cid = bot_cid
        if str(bot_cid) != str(audio_bot_cid):
            self.conn.clientmove(cid=audio_bot_cid, clid=bot_clid)
            self.logger.info(f"Client moved to cid:{audio_bot_cid}.")
        return

    def play_now(self):
        # 获取api中的now，并播放，尽可能少用，因为该操作会中止当前播放，而audiobot多次play容易出现阻塞。
        response = self.music_api.now()
        if not response.succeed:
            return
        song = response.data
        # =========================================
        # 获取link
        response = self.music_api.get_song_link(song.id)
        if not response.succeed:
            return
        link = response.data
        # =========================================
        response = self.audio_bot_api.play(link)
        if not response.succeed:
            self.logger.info(f"Play_now failed link: {link}")
            self.error(response.reason)
        return

    def update_play(self):
        response = self.audio_bot_api.is_playing()
        if not response.succeed:
            self.error(response.reason)
            return
        is_playing = response.data
        if not is_playing:
            self.music_api.next()
            self.play_now()
        return

    def update_info(self):
        response = self.audio_bot_api.get_song()
        if not response.succeed:
            return
        link = response.data['Link']
        if self.previous_link == link:
            return
        response = self.music_api.now()
        if not response.succeed:
            return
        song: Song = response.data
        response = self.music_api.get_avatar_link(song.id)
        if response.succeed:
            avatar = response.data
        else:
            avatar = ''
        singers = ' '.join(singer.name for singer in song.singers)
        self.audio_bot_api.set_bot_description(f"！！正在播放来自{singers}的{song.name}")
        self.audio_bot_api.set_bot_avatar(avatar)
        self.previous_link = link

    def update(self):
        """用于更新AudioBot的歌曲信息"""
        if not self.music_api:
            return
        self.update_play()
        self.update_info()

    def standby(self):
        # 长时间未操作进入standby状态
        self.update_music_api()
        if self.chat_enable:
            self.chat_enable = False
            self.send("那我先下线了喵~~")
        return

    def handle(self, event: TS3Event):
        parsed_event = event.parsed[0]
        self.logger.info(f"Received event: {parsed_event}")
        sender_name = parsed_event['invokername']
        sender_uid = parsed_event['invokeruid']
        self.targetmode = parsed_event['targetmode']
        sender = Sender(sender_name=sender_name, sender_uid=sender_uid)
        message: str = parsed_event['msg']
        command = None
        alias = None
        for cmd_command in self.commands:
            for cmd_alias in cmd_command.alias:
                if message.startswith(cmd_alias):
                    command = cmd_command.command
                    alias = cmd_alias
                    break
            if command is not None:
                break
        if command is None:
            self.default(sender, message)
        else:
            args = message.strip(alias).strip().split(' ')
            try:
                func = self.__getattribute__(f"{self.prefix}{command}")
            except AttributeError:
                return
            self.logger.info(f"Exec cmd_function: {func.__name__}, sender: {sender}, args: {args}.")
            func(sender, *args)
            return

    def send(self, msg: str, color: str = None, bold: bool = False):
        if int(self.targetmode) == 3:
            target = self.sid
        else:
            target = self.cid
        message = msg
        if color is not None:
            message = f"[color={color}]" + msg + "[/color]"
        if bold:
            message = f"[b]{message}[/b]"
        self.conn.sendtextmessage(targetmode=self.targetmode, target=target, msg=message)

    def success(self, msg: str):
        self.send(msg, color='green', bold=True)

    def error(self, msg: str):
        self.send(msg, color='red', bold=True)

    def info(self, msg: str):
        self.send(msg)

    def warning(self, msg: str):
        self.send(msg, bold=True)

    def play_song(self, song: Song):
        self.logger.info(f"Play {song}")
        link = self.music_api.get_song_link(song.id).data
        singers = ' '.join(singer.name for singer in song.singers)
        name = song.name
        response = self.audio_bot_api.play(link)
        if not response.succeed:
            self.error(response.reason)
            return
        self.music_api.current_insert(song)
        self.success(f"！！开始播放来自{singers}的{name}")
        return

    def add_song(self, list_id: str, song: Song):
        self.logger.info(f"Add {song}")
        singers = ' '.join(singer.name for singer in song.singers)
        name = song.name
        response = self.music_api.list_add(list_id, song)
        if not response.succeed:
            self.error(response.reason)
            return
        self.success(f"！！添加{singers}的{name}到歌单。")
        return

    def default(self, sender, *args):
        self.logger.info(f"Default sender: {sender}, args: {args}.")
        if self.chat_enable:
            self.cmd_chat(sender, *args)
        return

    def check_pet_api(self):
        if self.pet_api is None:
            self.info("宠物api未设置。")
            return False
        return True

    def check_tts_api(self):
        if self.tts_api is None:
            self.info("TTSapi未设置。")
            return False
        return True

    def confirm(self, sender: Sender, question: str, timeout: int = 5) -> bool:
        message: str = self.ask(sender, question + "[是/否]", timeout=timeout)
        if message.startswith("是"):
            return True
        return False

    def ask(self, sender: Sender, question: str, timeout: int = 10) -> str:
        self.logger.info(f"Ask sender:{sender}.")
        self.info(question + " >")
        event = None
        time_start = time.time()
        while time.time() - time_start < timeout:
            try:
                event = self.wait_event(timeout=1)
                if event.parsed[0]['invokeruid'] == sender.sender_uid:
                    break
            except TS3TimeoutError:
                continue
        if not event:
            self.info("未执行操作。")
            return ''
        parsed_event = event.parsed[0]
        self.logger.debug(f"Ask received event: {parsed_event}.")
        message: str = parsed_event['msg']
        return message.strip()

    def get_clid_from_uid(self, uid):
        ids = self.conn.clientgetids(cluid=uid)[0]
        if not ids:
            return None
        return ids[0]

    def get_info_from_uid(self, uid):
        clid = self.get_clid_from_uid(uid)
        if not clid:
            return None
        return self.conn.clientinfo(clid=clid)[0]

    def get_name_from_uid(self, uid):
        name = self.conn.clientgetnamefromuid(cluid=uid)[0]
        if not name:
            return None
        return name['name']

    # ========================================
    # 有关接口的cmd

    def cmd_show_apis(self, sender, *args):
        api_info_str = "[b][color=blue]接口状态[/color]\n"
        count = 1
        for api_id, api_info in sorted(self.music_apis.items(), key=lambda x: x[1]['priority'], reverse=True):
            api_info_str += f"[{count}]\tId: {api_id}\tApiType: {api_info['api'].__class__.__name__}\tStatus: {'[color=green]Available[/color]' if api_info['accessibility'] else '[color=red]Unavailable[/color]'}\t"
            if api_id == self.current_music_api:
                api_info_str += "\t<=正在使用"
            api_info_str += '\n'
            count += 1
        self.send(api_info_str)

    def cmd_set_priority(self, sender, *args):
        if args[0] == '':
            self.send("请输入接口Id。")
            return
        if len(args) < 2:
            self.send("请输入需要修改的优先级大小。")
            return
        try:
            priority = int(args[1])
        except ValueError:
            self.send("请输入数字。")
            return
        api_id = args[0]
        if api_id not in self.music_apis:
            self.error("未找到对应接口。")
        self.music_apis[api_id]['priority'] = priority
        self.success("修改成功。")

    def cmd_update_apis(self, sender, *args):
        self.update_music_api()
        self.success("刷新接口成功。")
        self.cmd_show_apis(sender)

    # ========================================

    # ========================================
    # 聊天cmd

    def cmd_chat(self, sender, *args):
        if self.chat_api is None:
            self.error("聊天api未设置。")
            return
        if args[0] == '':
            self.chat_enable = True
            self.chat_api.reset()
            self.info("聊天模式已开启喵~~")
            return
        if not self.chat_enable:
            return
        msg = args[0]
        response = self.chat_api.chat(f"{sender.sender_name}：{msg}")
        if not response.succeed:
            self.error(response.reason)
            return
        self.send(response.data)
        return

    # ========================================

    # ========================================
    # 帮助cmd

    def cmd_help(self, sender, *args):
        help_str = '[b][color=blue]食用方式[/color]\n'
        for command in self.commands:
            if command.example:
                examples_str = '，'.join(command.example)
            else:
                examples_str = '，'.join(command.alias)
            help_str += f"{command.help}\t功能：{command.command}\t指令：[color=green]{'，'.join(command.alias)}[/color]\t例子：{examples_str}\n"
        self.send(help_str)

    # ========================================

    # ========================================
    # 歌曲相关cmd
    def cmd_play(self, sender, *args):
        if args[0] == '':
            self.audio_bot_api.play()
            return
        self.info("正在搜索中....")
        response = self.music_api.search_songs(args[0], size=1)
        if not response.succeed:
            self.error(response.reason)
            return
        songs = response.data
        if not songs:
            response = self.music_api.get_suggest(args[0])
            if not response.succeed:
                self.error(response.reason)
            suggestions = response.data
            if suggestions:  # 如果suggest结果为非空则发送建议
                self.info(f"没有搜到{args[0]}哦，建议你搜搜[b]{'，'.join(suggestions)}[b]")
                return
            else:
                self.info("没有找到你想要的歌曲。")
        else:
            song = songs[0]
            self.play_song(song)
        return

    def cmd_play_id(self, sender, *args):
        if args[0] == '':
            self.warning("请跟上ID。")
            return
        self.info("正在搜索中....")
        song_id = re.sub(r'\D', '', args[0])
        response = self.music_api.get_songs(song_id)
        if not response.succeed:
            self.error(response.reason)
            return
        songs = response.data
        if not songs:
            self.info("没有找到对应ID的歌曲。")
        else:
            song = songs[0]
            self.play_song(song)
        return

    def cmd_add(self, sender, *args):
        if args[0] == '':
            self.audio_bot_api.play()
            return
        self.info("正在搜索中....")
        keys: str = args[0]
        keys = keys.replace(',', '|').replace('，', '|')
        for key in keys.split('|'):
            response = self.music_api.search_songs(key, size=1)
            if not response.succeed:
                self.error(response.reason)
                return
            songs = response.data
            if not songs:
                response = self.music_api.get_suggest(key)
                if not response.succeed:
                    self.error(response.reason)
                suggestions = response.data
                if suggestions:  # 如果suggest结果为非空则发送建议
                    self.info(f"没有搜到{key}哦，建议你搜搜[b]{'，'.join(suggestions)}[b]")
                    return
                else:
                    self.info("没有找到你想要的歌曲。")
            else:
                song = songs[0]
                self.add_song(self.music_api.current_list_id, song)
        return

    def cmd_add_id(self, sender, *args):
        if args[0] == '':
            self.warning("请跟上ID。")
            return
        self.info("正在搜索中....")
        keys: str = args[0]
        keys = keys.replace(',', '|').replace('，', '|')
        for key in keys.split('|'):
            song_id = re.sub(r'\D', '', key)
            response = self.music_api.get_songs(song_id)
            if not response.succeed:
                self.error(response.reason)
                return
            songs = response.data
            if not songs:
                self.info("没有找到对应ID的歌曲。")
            else:
                song = songs[0]
                self.add_song(self.music_api.current_list_id, song)
        return

    def cmd_search(self, sender, *args):
        if args[0] == '':
            return
        self.info("正在搜索中....")

        if len(args) == 2:
            try:
                size = int(args[1].strip())
            except ValueError:
                self.error("请输入正确的数字。")
                return
            response = self.music_api.search_songs(args[0], size=size)
        else:
            response = self.music_api.search_songs(args[0])
        if not response.succeed:
            self.error(response.reason)
            return
        songs = response.data
        if not songs:
            response = self.music_api.get_suggest(args[0])
            if not response.succeed:
                self.error(response.reason)
            suggestions = response.data
            if suggestions:  # 如果suggest结果为非空则发送建议
                self.info(f"没有搜到{args[0]}哦，建议你搜搜[b]{'，'.join(suggestions)}[b]")
                return
            else:
                self.info("没有找到你想要的歌曲。")
        else:
            infos = ["搜索到的结果如下内："]
            for song in songs:
                info_str = f"ID：{song.id}\t歌名：{song.name}\t歌手：{' '.join(singer.name for singer in song.singers)}"
                if song.album:
                    info_str += f"\t专辑：{song.album.name}"
                infos.append(info_str)
            self.info("[b]" + '\n'.join(infos) + "[/b]")

    def cmd_pause(self, sender, *args):
        self.audio_bot_api.pause()

    def cmd_show_list(self, sender, *args):
        if args[0] == '':
            list_id = "当前"
            response = self.music_api.current_show()
        else:
            list_id = args[0]
            response = self.music_api.list_show(list_id)
        if not response.succeed:
            self.error("未找到歌单ID请重试。")
            return
        playlist: PlayList = response.data
        if list_id == "当前":
            now_id = self.music_api.current_index
        else:
            now_id = -1
        songs = playlist.songs
        song_count = len(songs)
        song_list_str = f"[b][color=blue]{list_id}歌单 共{song_count}首歌[/color]\n"
        for index, song in enumerate(songs):
            song_info_str = f"[{str(index + 1).zfill(len(str(song_count)))}]\tID：{song.id.ljust(9, '-')}  {song.name}  {'，'.join(singer.name for singer in song.singers)}"
            if index == now_id:
                song_info_str = "[color=green]" + song_info_str + " <==正在播放 [/color]"
            song_list_str += song_info_str + '\n'
        self.send(song_list_str)
        return

    def cmd_next(self, sender, *args):
        response = self.music_api.next()
        if not response.succeed:
            self.error(response.reason)
            return
        self.play_now()
        self.success("切换到歌单下一首。")
        return

    def cmd_previous(self, sender, *args):
        response = self.music_api.previous()
        if not response.succeed:
            self.error(response.reason)
            return
        self.play_now()
        self.success("切换到歌单上一首。")
        return

    def cmd_jump(self, sender, *args):
        if args[0] == '':
            return
        try:
            index = int(args[0]) - 1
        except ValueError:
            self.info("？跳转[索引]")
            return
        response = self.music_api.jump(index)
        if not response.succeed:
            self.error(response.reason)
            return
        self.play_now()
        self.success(f"跳转到歌单第{index+1}首。")
        return

    def cmd_volume(self, sender, *args):
        if args[0] == '':
            value = ''
        else:
            try:
                value = str(int(args[0]))
            except ValueError:
                self.info("？音量 [大小]")
                return
        response = self.audio_bot_api.volume(value)
        if not response.succeed:
            self.error(response.reason)
            return
        if value == '':
            self.success(f"当前音量为：{response.data}")
        else:
            self.success(f"成功调节音量：{value}")
        return

    def cmd_clear(self, sender, *args):
        confirm = self.confirm(sender, "你确定要清空当前歌单吗？")
        if confirm:
            response = self.music_api.clear()
            if not response.succeed:
                self.error("清空歌单失败。")
                return
            self.audio_bot_api.clear()
            self.success("已为您清空歌单。")
        else:
            self.info("好的呢~")
        return

    def cmd_play_list(self, sender, *args):
        if args[0] == '':
            self.info("请输入歌单ID。")
            return
        response = self.music_api.list_play(args[0])
        if not response.succeed:
            self.error(response.reason)
            return
        self.play_now()
        self.success(f"！！开始播放歌单ID：{args[0]}")
        return

    def cmd_delete_list(self, sender, *args):
        if args[0] == '':
            self.info("请输入歌单ID。")
            return
        confirm = self.confirm(sender, "你确定要删除该歌单吗？")
        if not confirm:
            self.info("好的呢~")
            return
        response = self.music_api.list_delete(args[0])
        if not response.succeed:
            self.error(response.reason)
            return
        self.success("已为您删除歌单。")
        return

    def cmd_remove_item_list(self, sender, *args):
        if args[0] == '':
            self.info("请输入歌单ID。")
            return
        if args[1] == '':
            self.info("请输入歌曲序号。")
            return
        try:
            index = int(args[1]) - 1
        except ValueError:
            self.error("参数不正确。")
            return
        response = self.music_api.list_remove(args[0], index)
        if not response.succeed:
            self.error(response.reason)
            return
        self.success("删除成功！")
        return

    def cmd_remove_item_current(self, sender, *args):
        if args[0] == '':
            self.info("请输入歌曲序号。")
            return
        try:
            index = int(args[0]) - 1
        except ValueError:
            self.error("参数不正确。")
            return
        response = self.music_api.current_remove(index)
        if not response.succeed:
            self.error(response.reason)
            return
        self.success("删除成功！")
        if index == self.music_api.current_index:
            self.audio_bot_api.stop()
        return

    def cmd_add_item_list(self, sender, *args):
        if args[0] == '':
            self.info("请输入歌单ID。")
            return
        if args[1] == '':
            self.info("请输入歌曲名")
            return
        list_id = args[0]
        response = self.music_api.is_list_created(list_id)
        if not response.succeed:
            self.error(response.reason)
            return
        is_list_created = response.data
        if not is_list_created:
            self.error("未找到歌单。")
            return
        self.info("正在搜索中....")
        keys: str = args[1]
        keys = keys.replace(',', '|').replace('，', '|')
        for key in keys.split('|'):
            response = self.music_api.search_songs(key, size=1)
            if not response.succeed:
                self.error(response.reason)
                return
            songs = response.data
            if not songs:
                response = self.music_api.get_suggest(key)
                if not response.succeed:
                    self.error(response.reason)
                    return
                suggestions = response.data
                if suggestions:  # 如果suggest结果为非空则发送建议
                    self.info(f"没有搜到{key}哦，建议你搜搜[b]{'，'.join(suggestions)}[b]")
                    return
                else:
                    self.info("没有找到你想要的歌曲。")
                    return
            else:
                song = songs[0]
                self.add_song(list_id, song)
        return

    def cmd_add_id_item_list(self, sender, *args):
        if args[0] == '':
            self.info("请输入歌单ID。")
            return
        if args[1] == '':
            self.info("请输入歌曲名")
            return
        list_id = args[0]
        response = self.music_api.is_list_created(list_id)
        if not response.succeed:
            self.error(response.reason)
            return
        is_list_created = response.data
        if not is_list_created:
            self.error("未找到歌单。")
            return
        self.info("正在搜索中....")
        keys: str = args[1]
        keys = keys.replace(',', '|').replace('，', '|')
        for key in keys.split('|'):
            song_id = re.sub(r'\D', '', key)
            response = self.music_api.get_songs(song_id)
            if not response.succeed:
                self.error(response.reason)
                return
            songs = response.data
            if not songs:
                self.info("没有找到对应ID的歌曲。")
            else:
                song = songs[0]
                self.add_song(list_id, song)
        return

    def cmd_list_list(self, sender, *args):
        response = self.music_api.list_list()
        if not response.succeed:
            self.error(response.reason)
            return
        lists: Dict[str, PlayList] = response.data
        lists_info_str = "[b][color=blue]所有歌单[/color][/b]\n"
        for playlist_id, playlist in lists.items():
            lists_info_str += f"[b]ID：{playlist.id}\t歌曲数量：{len(playlist.songs)}[/b]\n"
        self.send(lists_info_str)
        return

    def cmd_save_current_list(self, sender, *args):
        list_id: str = self.ask(sender, "请输入要保存为的歌单名")
        if not list_id:
            return
        response = self.music_api.list_create(list_id)
        if not response.succeed:
            self.error(response.reason)
            return
        response = self.music_api.list_copy(self.music_api.current_list_id, list_id)
        if not response.succeed:
            self.error(response.reason)
            return
        self.success(f"成功保存当前歌单到{list_id}歌单")
        self.cmd_list_list(sender)
        return

    # ========================================

    # ========================================
    # 宠物相关cmd
    def cmd_pet_new(self, sender, *args):
        if not self.check_pet_api():
            return
        if self.pet_api.have_pet(sender.sender_uid):
            res = self.confirm(sender, "每个人只能创建一只宠物哦，是否要覆盖掉当前宠物？")
            if not res:
                self.info("好的呢")
                return
        msg = self.ask(sender, "请输入宠物描述（15秒内）", timeout=15)
        if not msg:
            return
        self.info("生成中....")
        pet_info: PetInfo = self.pet_api.new_pet(sender.sender_uid, msg)
        if not pet_info:
            self.error("创建宠物失败，请重试。")
            return
        self.success(f"创建宠物成功！恭喜{sender.sender_name}拥有了一只{pet_info.name}。")

    def cmd_pet_upgrade(self, sender, *args):
        if not self.check_pet_api():
            return
        if not self.pet_api.have_pet(sender.sender_uid):
            self.info("你还没有宠物呢。")
            return
        if not self.pet_api.upgradable(sender.sender_uid):
            self.info("你的宠物目前还不能升级呢。")
            return
        msg = self.ask(sender, "请输入技能描述（15秒内）", timeout=15)
        if not msg:
            return
        self.info("生成技能中....")
        skill = self.pet_api.upgrade_pet(sender.sender_uid, msg)
        if not skill:
            self.error("升级宠物失败，请重试。")
            return
        self.success(f"升级宠物成功！恭喜{sender.sender_name}的宠物获得了新技能{skill.name}。")

    def cmd_pet_list(self, sender, *args):
        if not self.check_pet_api():
            return

    def cmd_pet_feed(self, sender, *args):
        if not self.check_pet_api():
            return
        if not self.pet_api.have_pet(sender.sender_uid):
            self.info("你还没有宠物呢。")
            return
        res, reason = self.pet_api.feed_pet(sender.sender_uid)
        if reason == "NoFood":
            self.error("喂食失败！没有足够的食物。")
        elif reason == "Full":
            self.error("喂食失败！宠物还饱呢。")
        elif reason == "LevelUp":
            self.success("喂食成功！宠物升级！！！！！")
        elif reason == "Success":
            self.success("喂食成功！")

    def cmd_pet_show(self, sender, *args):
        if not self.check_pet_api():
            return
        if not self.pet_api.have_pet(sender.sender_uid):
            self.info("你还没有宠物呢。")
            return
        pet_info = self.pet_api.show_pet(sender.sender_uid)
        if pet_info is None:
            self.error("您还没拥有任何宠物呢。")
        skills_str = '\n'.join(
            [f'- 技能名称：{skill.name}  技能种类：{skill.type} 技能强度：{skill.capability}  技能描述：{skill.description}'
             for skill in pet_info.skills])
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
升级所需喂食次数：{pet_info.level - pet_info.feed_times + 1}
描述：{pet_info.description}
技能列表：
{skills_str}
""")

    def cmd_pet_delete(self, sender, *args):
        if not self.check_pet_api():
            return
        if not self.pet_api.have_pet(sender.sender_uid):
            self.info("你还没有宠物呢。")
            return
        confirm = self.confirm(sender, "你确定要删除你的宠物吗？")
        if not confirm:
            self.info("好的呢")
            return
        self.pet_api.delete_pet(sender.sender_uid)
        self.success("删除成功。")
        return

    def cmd_pet_battle_start(self, sender, *args):
        if not self.check_pet_api():
            return
        if not self.pet_api.have_pet(sender.sender_uid):
            self.info("你还没有宠物呢。")
            return
        if len(self.pet_api.battle_wait) < 2:
            self.cmd_pet_battle_list(sender)
            return
        self.info("[b]生成战斗中，请稍后")
        res: BattleResult = self.pet_api.battle_pet()
        if not res:
            self.error("生成战斗失败，请重试。")
            return
        self.success("[b]战斗开始！！！！！！！！！！！！！！")
        for r in res.rounds:
            time.sleep(0.5)
            self.send('[b]' + r)
        self.success(f"最终赢家为：{self.get_name_from_uid(res.winner)}")
        return

    def cmd_pet_battle_list(self, sender, *args):
        if not self.check_pet_api():
            return
        if not self.pet_api.battle_wait:
            self.info("当前没有宠物在等待战斗呢。")
            return
        battle_wait_str = '[b][color=blue]当前等待战斗的宠物[/color]\n'
        for pet in self.pet_api.battle_wait:
            battle_wait_str += f'\t- 来自{self.get_name_from_uid(pet.owner)}的{pet.name}\n'
        self.send(battle_wait_str)
        return

    def cmd_pet_battle_add(self, sender, *args):
        if not self.check_pet_api():
            return
        if not self.pet_api.have_pet(sender.sender_uid):
            self.info("你还没有宠物呢。")
            return
        self.pet_api.battle_add_pet(sender.sender_uid)
        self.success("宠物已成功加入战斗场。")
        return

    def cmd_checkin(self, sender, *args):
        if not self.check_pet_api():
            return
        if not self.pet_api.have_pet(sender.sender_uid):
            self.info("你还没有宠物呢。")
            return
        self.pet_api.add_food_pet(sender.sender_uid)
        self.success("签到成功，获得1食物。")
        return

    # ========================================

    # ========================================
    # TTS相关cmd
    def cmd_broadcast(self, sender, *args):
        if not self.check_tts_api():
            return
        if not args[0]:
            self.error("请输入广播内容。")
            return
        voice_id = "jlshim"
        if len(args) >= 2:
            voice_id = args[1]
        response = self.audio_bot_api.is_playing()
        if not response:
            self.error(response.reason)
            return
        response = self.audio_bot_api.play(self.tts_api.get(args[0], voice_id=voice_id, volume=200, speed=10).data)
        if not response.succeed:
            self.error(response.reason)
            return
        self.success("广播中...")
        time.sleep(1)
        return

    # ========================================

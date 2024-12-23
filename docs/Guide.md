# ts3MusicBot使用指南
## 目录

- [前言](#1-前言)

- [如何使用机器人](#2-如何使用机器人)
  - [开发音乐Api](#21-开发音乐api)
  - [注册音乐Api](#22-注册音乐api)
  - [注册指令](#23-注册指令)
  - [配置及启动](#24-配置及启动)

- [内置api说明](#3-内置api说明)
- [内置功能说明](#4-内置功能说明)
- [自定义的功能开发](#5-自定义的功能开发)
- [自定义的api开发](#6-自定义的api开发)


## 1 前言
这个机器人的初衷还是为了听音乐的，一开始的时候仍旧是依赖TS3AudioBot的歌单功能实现的，但是后面发现TS3AudioBot的歌单功能并不好用（比如并不能移除当前歌单的某首歌），于是所幸自己写了一个。

如果你想用尽量少的精力让这个机器人运行起来，你所要做的就是找到一个音乐API并且完成简单的部分开发，然后运行即可。指南中有完整手把手的开发教学。


## 2 如何使用机器人


### 2.1 开发音乐Api
由于版权问题，我不能够直接给出一些API，目前我自己的实现是在网上找了一些免费曲库并使用他们的API。所以实现一个音乐API的方法我尽量做到了精简，只需要实现五六个方法即可完成一个音乐API。你可以通过查看[示例api](../examples/ExampleMusicApi.py)来学习，或者跟着手册一步步进行。

首先有一些原则要说明，为了保证机器人的正常运转，API的开发中对返回格式有要求，尤其是不能够出现报错，你需要在API中处理所有的错误。当然我提供了一个函数装饰器来帮助实现。

#### 2.1.1 创建你的MusicApi类
自定义类并继承自MusicApi。
~~~python
from apis.muiscApi.MusicApi import MusicApiResponse, MusicApi

class MyMusicApi(MusicApi):
    pass
~~~

#### 2.1.2 导入装饰器
导入api装饰器。
~~~python
from apis.muiscApi.MusicApi import api
~~~
装饰器的源码如下，包裹上api装饰器后就不需要处理错误了，所有的错误都在装饰器中统一处理，如果你需要更详细的错误输出，你也可以自己自定义一个装饰器。总之原则就是api不会报错中断而是会返回错误。
~~~python
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
~~~
#### 2.1.3 Api返回值
所有api的返回值都应当是一个[BaseApiResponse](../apis/BaseApi.py)实例。在MusicApi中为继承自[BaseApiResponse](../apis/BaseApi.py)的MusicApiResponse。
~~~python
class BaseApiResponse(BaseModel):
    succeed: bool       # 用于表示操作是否出错
    reason: str = None  # 携带出错信息
    data: Any = None    # 携带返回结果

    @classmethod
    def success(cls, data: Any = None):
        return cls(succeed=True, reason="Success", data=data)

    @classmethod
    def failure(cls,reason: str):
        return cls(succeed=False, reason=reason)
~~~    
当**操作正常被执行**了则`succeed`域就应当为`True`。比如`is_playing`接口需要返回当前是否正在播放歌曲，则应该这样编写。
~~~python
@api
def is_playing():
    .....
    if is_playing:
        return MusicApiResponse.success(True)
    else:
        return MusicApiResponse.success(False)
~~~
而不是
~~~python
@api
def is_playing():
    .....
    if is_playing:
        return MusicApiResponse.success()
    else:
        return MusicApiResponse.failure()
~~~

#### 2.1.4 开始完成函数
在MusicApi中有以下这些函数需要完成。以下注释中所声明的返回值都是MusicApiResponse.success()中所携带的data域的类型。
~~~python
class MyMusicApi(MusicApi):
    @api
    def available(self):
        # 用于检测当前api是否可用。
        pass

    @api
    def search_songs(self, key: str, size: int = 20, max_retries: int = 2):
        # 通过key来获取歌词
        # key 为搜索的关键词，比如"陈奕迅"
        # data 返回值应该为一个list[Song]
        pass

    @api
    def get_songs(self, ids:Union[str,list]):
        # 通过id来获取歌曲
        # ids 为搜索的歌曲id，比如"132"或["123","456"]
        # data 返回值应该为一个list[Song]
        pass
    
    @api
    def get_suggest(self, key, max_retries: int = 2):
        # key 为搜索的key
        # data 返回值应该为一个建议搜索的列表，list[str]
        pass

    @api
    def get_song_link(self, song_id: str, quality: int = 320, file_format: str = "mp3"):
        # song_id 为搜索的song_id歌曲id
        # data 返回值应该为一个歌曲资源的链接，比如"http://123.456.com/music/api/123.mp3"，str
        pass

    @api
    def get_avatar_link(self, song_id: str, quality: int = 500, file_format: str = "jpg"):
        # song_id 为搜索的song_id歌曲id
        # data 返回值应该为一个歌曲封面图片资源的链接，比如"http://123.456.com/music/api/123.jpg"，str
        pass
~~~
一个简单的示例如下，也可以查看[示例api](../examples/ExampleMusicApi.py)
~~~python
class MyMusicApi(MusicApi):
    # 以下api需要根据不同的api调整。
    @api
    def available(self):
        response = self.search_songs("陈奕迅")
        if not response.succeed:
            return response
        if not response.data:
            return MusicApiResponse.failure("Unavailable")
        return MusicApiResponse.success()

    @api
    def search_songs(self, key: str, size: int = 20, max_retries: int = 2):
        search_url = self.url + f"/api/music/search"
        params = {"key": key, "pageIndex": 1, "pageSize": size}
        rep = None
        for _ in range(max_retries):
            try:
                rep = requests.get(search_url, params=params)
                break
            except Exception:
                continue
        if rep is None:
            raise requests.exceptions.RequestException
        if 'data' in rep.json()['data']:
            data = rep.json()['data']['data']
            songs=[]
            for song_data in data:
                songs.append(Song(**song_data))
            return MusicApiResponse.success(songs)
        return MusicApiResponse.success([])

    @api
    def get_songs(self, ids:Union[str,list]):
        if type(ids) is str:
            ids=[ids]
        url = self.url + f"/api/music/song"
        params = {"ID": ','.join(ids)}
        rep = requests.get(url, params=params)
        data = rep.json()['data']
        songs = []
        for song_data in data:
            song = Song(**song_data)
            songs.append(song)
        return MusicApiResponse.success(songs)

    @api
    def get_suggest(self, key, max_retries: int = 2):
        # 这里如果没有搜索建议功能可以直接这样写从而始终返回空列表
        return MusicApiResponse.success([])

    @api
    def get_song_link(self, song_id: str, quality: int = 320, file_format: str = "mp3"):
        url = self.url + f"/api/music/url"
        params = {"ID": song_id, "quality": quality, "format": file_format}
        return MusicApiResponse.success(url + "?" + urlencode(params))

    @api
    def get_avatar_link(self, song_id: str, quality: int = 500, file_format: str = "jpg"):
        url = self.url + f"/api/music/url"
        params = {"ID": song_id, "quality": quality, "format": file_format}
        return MusicApiResponse.success(url + "?" + urlencode(params))
~~~

### 2.2 注册音乐Api
由于机器人内置了多个MusicApi接口管理功能，所以可以同时编写好几个曲库的api，并注册设置优先级，当某个api寄了之后机器人会自动切换。

注册Api的方法需要传入api，apiId，优先级（优先级越大则越前面）。
~~~python
def register_music_api(self, music_api: MusicApi, api_id: str, priority: int = 100):
    pass
~~~
示例注册如下。
~~~python
bot = TS3Bot('serveradmin', password, bot_api, server_host)
bot.register_music_api(MyMusicApi("www.xxx.com"),"default",priority=50)
~~~

### 2.3 注册指令
内置了很多指令，当然也可以根据需要修改。command是指令的函数名后缀，alias是指令触发的关键词，help是指令解释。
~~~python
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
~~~
注册指令
~~~python
from TS3Bot import TS3Bot,my_commands
bot=....
bot.register_commands(my_commands)
~~~
当前的匹配方式仍旧是顺序匹配，所以部分较短的有重合的指令请放在后面注册，以避免冲突，后续可能更新为最长匹配。

指令匹配的逻辑是获取前缀和后缀拼接后的类方法名，进行调用。
~~~python
    ....
    try:
        func = self.__getattribute__(f"{self.prefix}{command}")
    except AttributeError:
        return
    self.logger.info(f"Exec cmd_function: {func.__name__}, sender: {sender}, args: {args}.")
    func(sender, *args)
    ....
~~~

### 2.4 配置及启动
完成了MusicApi的开发之后就可以启动机器人了。最基础功能的bot如下。
~~~python
from MyMusicApi import MyFirstMusicApi,MySecondMusicApi
from apis.chatApi.ChatApi import ChatApi
from apis.petApi.PetApi import PetApi
from apis.ttsApi.TTSApi import TTSApi
from TS3Bot import TS3Bot,my_commands
if __name__ == '__main__':
    bot_api = "http://xxx.xxx.xxx.xxx:58913" # audioBot的web api地址，默认端口为58913
    password= 'password' # admin serverquery的密码
    server_host = 'xxx.xxx.xxx.xxx' # ts3服务器地址
    bot = TS3Bot('serveradmin', password, bot_api, server_host)
    first = MyFirstMusicApi("https://www.first.music/") # 自己编写的api
    second = MySecondMusicApi("https://www.second.music/") # 自己编写的api
    bot.register_music_api(first,"First",priority=50)
    bot.register_music_api(second,"Second")
    bot.register_commands(my_commands)
    bot.run()
~~~

启用所有功能的示例如下。
~~~python
from MyMusicApi import MyFirstMusicApi,MySecondMusicApi
from apis.chatApi.ChatApi import ChatApi
from apis.petApi.PetApi import PetApi
from apis.ttsApi.TTSApi import TTSApi
from TS3Bot import TS3Bot,my_commands
if __name__ == '__main__':
    bot_api = "http://xxx.xxx.xxx.xxx:58913" # audioBot的web api地址，默认端口为58913
    chat_api_key = "sk-xxxxxxxxxxxxx" # 通义的api_key
    tts_api = "xxxx" # ttsapi的接口
    password= 'password' # admin serverquery的密码
    server_host = 'xxx.xxx.xxx.xxx' # ts3服务器地址
    bot = TS3Bot('serveradmin', password, bot_api, server_host)
    first = MyFirstMusicApi("https://www.first.music/")
    second = MySecondMusicApi("https://www.second.music/")
    bot.register_music_api(first,"First",priority=50)
    bot.register_music_api(second,"Second")
    bot.register_commands(my_commands)
    bot.chat_api = ChatApi(chat_api_key)    # ChatApi是用于聊天的
    bot.pet_api = PetApi(chat_api_key)  # PetApi是用于宠物
    bot.tts_api = TTSApi(tts_api)   # TTSApi
    bot.run()
~~~


## 3 内置api说明
### 3.1 AudioBotApi
### 3.2 ChatApi
### 3.2 MusicApi
### 3.2 PetApi
### 3.2 TTSApi

## 4 内置功能说明
待完善

## 5 自定义的功能开发
待完善

## 6 自定义的Api开发
待完善

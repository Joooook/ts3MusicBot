# ts3MusicBot
- [English](README_en.md)
- [Zh](README.md)
## 👋Introduction
A simple python bot based on TS3AudioBot for teamspeak3.

基于TS3AudioBot的简易teamspeak3机器人框架。

## 🚩Features
- 🎵基础音乐功能
  - 播放音乐
  - 歌单管理
  - 多曲库API管理
  - ....
- 🤖聊天功能：接入大模型供聊天。
- 🐶宠物功能：创建宠物并进行战斗。
- 📢广播功能: TTS广播。
- 自定义指令。
- 自定义API。
- ....
<div align="center"> 
<img src="imgs/help.png" alt="help" style="border-radius: 20px;" width="500px"/>
<img src="imgs/pet.jpg" alt="pet" style="border-radius: 20px;" width="500px"/>
<img src="imgs/chat.png" alt="chat" style="border-radius: 20px;" width="500px"/>
<img src="imgs/playlist.png" alt="playlist" style="border-radius: 20px;" width="500px"/>
</div>

## ⚙️Installation
首先必须安装[TS3AudioBot](https://github.com/Splamy/TS3AudioBot)。
~~~bash
git clone https://github.com/Joooook/ts3MusicBot
pip install -r requirements.txt
~~~

## ▶️Quick Start
请务必查看[使用指南](docs/Guide.md)。
~~~python
from apis.chatApi.ChatApi import ChatApi
from apis.petApi.PetApi import PetApi
from apis.ttsApi.TTSApi import TTSApi
from TS3Bot import TS3Bot,my_commands
from examples.ExampleMusicApi import ExampleMusicApi
if __name__ == '__main__':
    bot_api = "http://x.x.x.x:58913"
    chat_api_key = "sk-xxxxxxxxxxx"
    tts_api = "www.?.?"
    password= 'password'
    server_host = 'xxx.xxx.xxx.xxx'
    bot = TS3Bot('serveradmin', password, bot_api, server_host)
    # 创建并注册api
    example_music_api = ExampleMusicApi("https://www.xxxxxxx.xxxxx/")
    bot.register_music_api(example_music_api,"default",priority=50)
    bot.chat_api = ChatApi(chat_api_key)
    bot.pet_api = PetApi(chat_api_key)
    bot.tts_api = TTSApi(tts_api)
    # 注册指令
    bot.register_commands(my_commands)
    bot.run()
~~~
## ⚠️Notice
尽管机器人内置了很多基础功能，本项目也并非一个开箱即用的项目，需要进行二次开发，尤其是音乐API部分。


## 👉️Reference

- [ZHANGTIANYAO1/TS3AudioBot-NetEaseCloudmusic-plugin](https://github.com/ZHANGTIANYAO1/TS3AudioBot-NetEaseCloudmusic-plugin)
- [Splamy/TS3AudioBot](https://github.com/Splamy/TS3AudioBot)
- [benediktschmitt/py-ts3](https://github.com/benediktschmitt/py-ts3)
- [Binaryify/NeteaseCloudMusicApi](https://github.com/Binaryify/NeteaseCloudMusicApi)

## 💭Murmurs
一开始我在我的服务器上使用的是 [ZHANGTIANYAO1/TS3AudioBot-NetEaseCloudmusic-plugin](https://github.com/ZHANGTIANYAO1/TS3AudioBot-NetEaseCloudmusic-plugin)。 但是由于不可抗力网易云音乐的API现在不能用了很多歌都听不了了。因此我干脆自己写一个。但是Teamspeak又没有Python SDK，所以我只好用[pyts3](https://github.com/benediktschmitt/py-ts3)来配合[Ts3AudioBot](https://github.com/Splamy/TS3AudioBot)来实现。Python的易扩展性显然更适合开发机器人。

本项目仅抛砖引玉，欢迎催更。

## ☕️Donate
请我喝杯奶茶吧。
<div align="center"> 
<a href="https://afdian.com/item/2a0e0cdcadf911ef9f725254001e7c00">
  <img src="https://s2.loli.net/2024/11/29/1JBxzphs7V6WcK9.jpg" width="300px">
</a>
</div>

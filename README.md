# ts3MusicBot
# Introduction
A simple bot framework based on TS3AudioBot for teamspeak3.

# Features
- 基础音乐功能
  - 播放音乐
  - 歌单操作
- 聊天功能：与ai聊天。
- 宠物功能：创建自己的宠物并对战。
- 广播功能：TTS播报。
- 自定义命令
- 自定义api

# Installation
Make sure you have installed the [TS3AudioBot](https://github.com/Splamy/TS3AudioBot)   .
~~~bash
pip install -r requirements.txt
~~~

# Usage
~~~python
from apis.muiscApi.MusicApi import MusicApi
from apis.chatApi.ChatApi import ChatApi
from apis.petApi.PetApi import PetApi
from apis.ttsApi.TTSApi import TTSApi
from bot import AudioBot

if __name__ == '__main__':
    bot_api = "http://xxx.xxx.xxx.xxx:58913"
    chat_api_key = "sk-xxxxxxxx"
    tts_api = "https://xxxxxxx"
    music_api = MusicApi("https://xxxx", "xxxx")
    password= 'xxxxxxxxxxxxxx'
    server_host = 'localhost'
    bot = AudioBot('serveradmin', password, bot_api, music_api, server_host)
    bot.chat_api = ChatApi(chat_api_key)
    bot.pet_api = PetApi(chat_api_key)
    bot.tts_api = TTSApi(tts_api)
    bot.run()
~~~
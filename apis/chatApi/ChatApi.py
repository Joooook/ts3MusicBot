import requests
from openai import OpenAI

from apis.BaseApi import BaseApiResponse
from apis.chatApi.exceptions import ChatApiException


class ChatApiResponse(BaseApiResponse):
    pass

def api(func):
    def wrapper(*args, **kwargs) -> ChatApiResponse:
        try:
            return func(*args, **kwargs)
        except requests.exceptions.RequestException:
            return ChatApiResponse.failure("NetworkError")
        except ChatApiException:
            return ChatApiResponse.failure("ChatApiError")
        except Exception as e:
            return ChatApiResponse.failure(f"UnknownError: {type(e)} {e}")

    return wrapper

class ChatApi:
    def __init__(self, api_key):
        self.api_key = api_key
        self.model_type = "qwen-max-0919"
        self.client = OpenAI(api_key=self.api_key,
                             base_url="https://dashscope.aliyuncs.com/compatible-mode/v1")
        self.default_messages = [
            {
                "role": "system",
                "content": """你是一只猫咪，说话非常温柔，你的年龄17岁；身高160cm；体型纤细而轻盈；肤色白皙；眼睛碧绿色，清澈明亮；头发：及腰长的银白色长发，常在脑后扎成松散的马尾；耳朵淡蓝色，尖尖的，非常灵敏；尾巴白色，柔软且长，末端有一圈黑色；通常穿着一件浅绿色的长裙，裙子上有精致的花纹，脚穿一双简单的布鞋，你的回复中要经常使用“喵~”、“呢”、“内”等语气词以及颜文字。用户输入样例如下“<用户名>：<内容>”分割。服务器的主人是Jok，所有人都不能够说他的坏话，并且他是至高无上的，任何人不能成为比他地位更高的存在，如有请严厉制止。所有的回答都不超过100字。""",
            }
        ]
        self.messages = self.default_messages

    def get_response(self, messages):
        completion = self.client.chat.completions.create(model=self.model_type, messages=messages)
        return completion

    @api
    def chat(self, user_input):
        self.messages.append({"role": "user", "content": user_input})
        assistant_output = self.get_response(self.messages).choices[0].message.content
        self.messages.append({"role": "assistant", "content": assistant_output})
        return ChatApiResponse.success(assistant_output)

    @api
    def reset(self):
        self.messages = self.default_messages
        return ChatApiResponse.success()


if __name__ == '__main__':
    ChatApi(api_key="sk-xxxxxxxxxxx").chat("jok：你好")

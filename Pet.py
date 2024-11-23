import json
import os.path
import pickle
from datetime import datetime, timedelta
from enum import EnumType, Enum
from typing import Dict
import pytz
from openai import OpenAI
from pydantic import BaseModel


class SkillType(Enum):
    ATTACK = "attack"
    DEFENSE = "defense"

class GetPetResponse(BaseModel):
    name: str
    species: str
    description: str
    health: int
    height : int
    weight: int


class PetApi:
    def __init__(self, api_key):
        self.api_key = api_key
        self.client = OpenAI(api_key=self.api_key,
                             base_url="https://dashscope.aliyuncs.com/compatible-mode/v1")
        self.file_name = "pet_list.pickle"
        if os.path.exists(self.file_name):
            self.pet_dict=pickle.load(open(self.file_name, 'rb'))
        else:
            self.pet_dict={}


    def get_response(self, messages):
        completion = self.client.chat.completions.create(model="qwen-plus", messages=messages)
        return completion

    def get_pet(self, owner, user_input):
        messages = [{
            "role": "system",
            "content": """请参考用户的输入，生成指定属性的宠物json，对于用户没有给出的请推理思考产生。请严格按照以下格式返回结果
            {
                "name":"示例姓名",
                "species":"示例种族",
                "description":"示例描述",
                "health": 生命值(int)
                "height": 身高(int)
                "weight": 体重(int)
            }
            """,
        }, {"role": "user", "content": user_input}]
        try:
            assistant_output = self.get_response(messages).choices[0].message.content
        except Exception:
            return None
        response = json.loads(assistant_output)
        response = GetPetResponse(**response)
        new_pet = Pet.create_pet(owner,response)
        self.pet_dict[owner]=new_pet
        self.save()
        return new_pet

    def feed(self,owner):
        self.pet_dict[owner]


    def save(self):
        pickle.dump(self.pet_dict, open("pet_list.pickle", "wb"))

class Pet:
    class Skill:
        def __init__(self, name, skill_type: SkillType):
            self.name = name
            self.type = skill_type
            self.capability = 10

    def __init__(self, owner:str, name:str, species:str, health:int, height:int, weight:int, description:str):
        self.owner = owner
        self.name = name
        self.species = species
        self.health = health
        self.height = height
        self.weight = weight
        self.description = description
        self.level = 0
        self.food_amount = 0
        self.last_feed = datetime.now(tz=pytz.timezone('Asia/Shanghai'))
        self.skills=["逃跑"]



    def feed(self):
        if self.food_amount == 0:
            return "NoFood"
        current_time = datetime.now(tz=pytz.timezone('Asia/Shanghai'))
        if current_time - self.last_feed < timedelta(hours=6):
            return "Full"
        self.food_amount -= 1
        return "Success"

    def upgrade(self):
        self.level += 1
        return self.level

    def display_info(self):
        print(f"名字: {self.name}")
        print(f"种类: {self.species}")
        print(f"等级: {self.level}")
        print(f"饥饿度: {self.hunger}")

    @staticmethod
    def create_pet(owner, response:GetPetResponse):
        return Pet(owner=owner,name=response.name,species=response.species,health=response.health,height=response.height,weight=response.weight,description=response.description)



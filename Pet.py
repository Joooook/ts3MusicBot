import json
import os.path
import pickle
from datetime import datetime, timedelta
from enum import EnumType, Enum
from typing import Dict, List
import pytz
from openai import OpenAI
from pydantic import BaseModel

class GetPetResponse(BaseModel):
    name: str
    species: str
    description: str
    health: int
    height : int
    weight: int

class Skill(BaseModel):
    name: str
    type: str
    capability:int
    description: str

class PetInfo(BaseModel):
    owner: str
    name: str
    species: str
    description: str
    health: int
    height : int
    weight: int
    level : int
    upgrade_times : int
    food_amount : int
    last_feed : datetime
    skills : List[Skill]

class PetApi:
    def __init__(self, api_key):
        self.api_key = api_key
        self.client = OpenAI(api_key=self.api_key,
                             base_url="https://dashscope.aliyuncs.com/compatible-mode/v1")
        self.file_name = "pet_list.pickle"
        if os.path.exists(self.file_name):
            self.pet_dict=pickle.load(open(self.file_name, 'rb'))
        else:
            self.pet_dict: Dict[str,Pet]={}


    def get_response(self, messages):
        completion = self.client.chat.completions.create(model="qwen-plus", messages=messages)
        return completion

    def new_pet(self, owner, user_input):
        """
        创建新宠物
        :param owner:
        :param user_input:
        :return: 返回新宠物的info
        """
        messages = [{
            "role": "system",
            "content": """请参考用户的输入，生成指定属性的宠物json，对于用户没有给出的请推理思考产生。请严格按照以下格式返回结果
            {
                "name":"示例姓名",
                "species":"示例种族",
                "description":"示例描述",
                "health": 生命值(int)
                "height": 身高(int 单位cm)
                "weight": 体重(int 单位kg)
            }
            """,
        }, {"role": "user", "content": user_input}]
        try:
            assistant_output = self.get_response(messages).choices[0].message.content
            response = json.loads(assistant_output)
            response = GetPetResponse(**response)
        except Exception:
            return None
        new_pet = Pet.create_pet(owner,response)
        self.pet_dict[owner]=new_pet
        self.save()
        return new_pet

    def delete_pet(self, owner):
        self.pet_dict.pop(owner)
        self.save()
        return

    def show_pet(self,owner:str):
        """
        返回对应主人的PetInfo
        :param owner:
        :return: PetInfo
        """
        return self.pet_dict[owner].get_info()

    def add_food_pet(self,owner:str):
        """
        返回对应主人的PetInfo
        :param owner:
        :return: PetInfo
        """
        self.pet_dict[owner].food_amount += 1
        return

    def list_pets(self):
        """
        :return: List[PetInfo]
        """
        return [pet.get_info() for pet in self.pet_dict.values()]

    def feed_pet(self, owner:str):
        res,reason = self.pet_dict[owner].feed()
        self.save()
        return res,reason

    def get_new_skill(self,owner,user_input) -> Skill:
        messages = [{
            "role": "system",
            "content": f"宠物的json格式基本信息如下{self.pet_dict[owner].get_info().model_dump_json()}",
        },{
            "role": "system",
            "content": """请参考用户的输入和宠物基本信息，生成指定的技能，对于用户没有给出的请推理思考产生。请严格按照以下格式返回结果
                    {
                        "name":"技能名称",
                        "type":"技能种类",
                        "capability": 技能强度(int),
                        "description":"技能描述"(小于20个字),
                    }""",
        }, {"role": "user", "content": user_input}]
        try:
            assistant_output = self.get_response(messages).choices[0].message.content
            response = json.loads(assistant_output)
            new_skill = Skill(**response)
        except Exception:
            return None
        return new_skill

    def upgrade_pet(self,owner:str,user_input:str) -> Skill:
        skill = self.get_new_skill(user_input)
        if skill is None:
            return None
        pet=self.pet_dict[owner]
        pet.skills.append(skill)
        pet.upgrade()
        self.save()
        return skill


    def save(self):
        pickle.dump(self.pet_dict, open("pet_list.pickle", "wb"))

    def have_pet(self,owner):
        if owner in self.pet_dict.keys():
            return True
        else:
            return False

    def upgradable(self,owner):
        if self.pet_dict[owner].upgrade_times > 0:
            return True
        return False

class Pet:
    def __init__(self, owner:str, name:str, species:str, health:int, height:int, weight:int, description:str):
        self.owner = owner
        self.name = name
        self.species = species
        self.health = health
        self.height = height
        self.weight = weight
        self.description = description
        self.level = 0
        self.upgrade_times = 0
        self.food_amount = 0
        self.feed_times = 0
        self.last_feed = datetime.now(tz=pytz.timezone('Asia/Shanghai'))
        self.skills=[Skill(name="小拳拳",type="攻击",capability=1,description="初始技能")]

    def feed(self):
        if self.food_amount == 0:
            return False,"NoFood"
        current_time = datetime.now(tz=pytz.timezone('Asia/Shanghai'))
        if current_time - self.last_feed < timedelta(seconds=1):
            return False,"Full"
        self.food_amount -= 1
        self.feed_times += 1
        if self.feed_times >= self.level+1:
            self.upgrade_times += 1
            self.feed_times = 0
            return True, "LevelUp"
        return True,"Success"

    def upgrade(self):
        if self.upgrade_times == 0:
            return False, "NoTimes"
        self.level += 1
        self.upgrade_times -= 1
        return True, "Success"

    def get_info(self) -> PetInfo:
        pet_info = PetInfo(
            owner=self.owner,
            name=self.name,
            species=self.species,
            health=self.health,
            height=self.height,
            weight=self.weight,
            description=self.description,
            upgrade_times=self.upgrade_times,
            level=self.level,
            food_amount=self.food_amount,
            last_feed=self.last_feed,
            skills=self.skills
        )
        return pet_info

    @staticmethod
    def create_pet(owner, response:GetPetResponse):
        return Pet(owner=owner,name=response.name,species=response.species,health=response.health,height=response.height,weight=response.weight,description=response.description)



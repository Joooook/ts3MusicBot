import json
import os.path
import pickle
import re
from datetime import datetime
from typing import Dict, List, Union
from openai import OpenAI
from pydantic import BaseModel

from apis.petApi.Pet import Pet


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
    feed_times : int
    last_feed : datetime
    skills : List[Skill]

class BattleResult(BaseModel):
    winner : str
    rounds : List[str]

class PetApi:
    def __init__(self, api_key):
        self.api_key = api_key
        self.client = OpenAI(api_key=self.api_key,
                             base_url="https://dashscope.aliyuncs.com/compatible-mode/v1")
        self.file_name = "../../pet_list.pickle"
        self.battle_wait: list[Pet]= []
        if os.path.exists(self.file_name):
            self.pet_dict=pickle.load(open(self.file_name, 'rb'))
        else:
            self.pet_dict: Dict[str, Pet]={}

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
        new_pet = Pet.create_pet(owner, response)
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

    def get_new_skill(self,owner,user_input) -> Union[Skill,None]:
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

    def upgrade_pet(self,owner:str,user_input:str) -> Union[Skill,None]:
        skill = self.get_new_skill(owner,user_input)
        if skill is None:
            return None
        pet=self.pet_dict[owner]
        pet.skills.append(skill)
        pet.upgrade()
        self.save()
        return skill

    def battle_pet(self):
        if not self.battle_wait:
            return None
        description = ''
        for index,pet in enumerate(self.battle_wait):
            description += f"第index: {index}只宠物：{pet.get_info().model_dump_json()}\n\n"
        messages = [{
            "role": "system",
            "content": description,
        }, {"role": "system", "content": """请模拟这些宠物回合制战斗，每回合描述以|分隔，回合数不大于12。请尽量让战斗过程曲折离奇包含战斗数值，最后一回合仅以[x]表示最终赢家（比如[1]表示宠物1获胜）。
        请严格按照以下格式输出：
        回合描述|回合描述|回合描述|回合描述|回合描述|[index]"""}]
        try:
            assistant_output = self.get_response(messages).choices[0].message.content
            rounds = assistant_output.split('|')
            winner_index = int(re.findall(r"\[(\d+)]",assistant_output)[0])
            winner = self.battle_wait[winner_index].owner
            result = BattleResult(winner=winner,rounds=rounds[:-1])
        except Exception as e:
            print(e)
            return None
        self.battle_wait.clear()
        self.save()
        return result

    def battle_add_pet(self,owner:str):
        if self.pet_dict[owner] in self.battle_wait:
            return
        self.battle_wait.append(self.pet_dict[owner])
        return

    def save(self):
        pickle.dump(self.pet_dict, open("../../pet_list.pickle", "wb"))

    def have_pet(self,owner):
        if owner in self.pet_dict.keys():
            return True
        else:
            return False

    def upgradable(self,owner):
        if self.pet_dict[owner].upgrade_times > 0:
            return True
        return False



from datetime import datetime, timedelta
from typing import List

import pytz
from pydantic import BaseModel
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
            skills=self.skills,
            feed_times=self.feed_times
        )
        return pet_info

    @staticmethod
    def create_pet(owner, response):
        return Pet(owner=owner,name=response.name,species=response.species,health=response.health,height=response.height,weight=response.weight,description=response.description)



from pydantic import BaseModel, Field
from typing import List, Optional


class Singer(BaseModel):
    name:str
    id:str

class Album(BaseModel):
    name:str
    id:str

class Song(BaseModel):
    link:str
    id:str
    name:str
    singers:List[Singer]
    album:Optional[Album]=None

class PlayList(BaseModel):
    id:str
    songs:List[Song]

from pydantic import BaseModel


class Sender(BaseModel):
    sender_name:str
    sender_uid:str
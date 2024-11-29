from typing import List

from pydantic import BaseModel


class Command(BaseModel):
    command: str
    alias: List[str]
    help: str = ''
    example: List[str] = []
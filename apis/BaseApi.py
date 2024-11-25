from abc import ABC,abstractmethod
from typing import Any

from pydantic import BaseModel


class BaseApiResponse(BaseModel):
    succeed: bool
    reason: str = None
    data: Any = None

    @classmethod
    def success(cls, data: Any = None):
        return cls(succeed=True, reason="Success", data=data)

    @classmethod
    def failure(cls,reason: str):
        return cls(succeed=False, reason=reason)

class BaseApi(ABC):
    pass


if __name__ == '__main__':
    print(BaseApiResponse.success({'success': True}))
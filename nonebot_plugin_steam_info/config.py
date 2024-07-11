from typing import Optional, Union, List
from pydantic import BaseModel, validator


class Config(BaseModel):
    steam_api_key: Union[str, List[str]]
    proxy: Optional[str] = None
    steam_request_interval: int = 300  # seconds
    steam_broadcast_type: str = "part"  # all, part, none
    steam_disable_broadcast_on_startup: bool = False

    @validator("steam_api_key", pre=True)
    def ensure_list(cls, v):
        if isinstance(v, str):
            return [v]
        return v

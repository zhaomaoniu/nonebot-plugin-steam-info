from typing import Optional, Union, List
from pydantic import BaseModel, validator


class Config(BaseModel):
    steam_api_key: Union[str, List[str]]
    proxy: Optional[str] = None
    steam_request_interval: int = 300  # seconds
    steam_broadcast_type: str = "part"  # all, part, none
    steam_disable_broadcast_on_startup: bool = False
    steam_font_regular_path: Optional[str] = "fonts/MiSans-Regular.ttf"
    steam_font_light_path: Optional[str] = "fonts/MiSans-Light.ttf"
    steam_font_bold_path: Optional[str] = "fonts/MiSans-Bold.ttf"

    @validator("steam_api_key", pre=True)
    def ensure_list(cls, v):
        if isinstance(v, str):
            return [v]
        return v

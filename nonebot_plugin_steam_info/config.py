import re
from typing import Optional, Union, List
from pydantic import BaseModel, validator


class Config(BaseModel):
    steam_api_key: Union[str, List[str]]
    steam_blocked_appids: Union[str, List[str]] = []
    proxy: Optional[str] = None
    steam_request_interval: int = 300  # seconds
    steam_broadcast_type: str = "part"  # all, part, none
    steam_disable_broadcast_on_startup: bool = False
    steam_font_regular_path: Optional[str] = "fonts/MiSans-Regular.ttf"
    steam_font_light_path: Optional[str] = "fonts/MiSans-Light.ttf"
    steam_font_bold_path: Optional[str] = "fonts/MiSans-Bold.ttf"
    
    # 新增定时开关配置
    steam_schedule_enabled: int = 0  # 0: 禁用定时开关, 1: 启用定时开关
    steam_schedule_open_time: str = "08:00"
    steam_schedule_close_time: str = "23:00"

    @validator("steam_api_key", pre=True)
    def ensure_list(cls, v):
        if isinstance(v, str):
            return [v]
        return v
    
    @validator("steam_blocked_appids", pre=True)
    def validate_steam_blocked_appids(cls, v):
        if isinstance(v, str):
            return [id.strip() for id in v.split(",") if id.strip()]
        return v if isinstance(v, list) else []
    
    @validator("steam_schedule_close_time", "steam_schedule_open_time")
    def validate_time_format(cls, v):
        if not re.match(r"^([01]\d|2[0-3]):([0-5]\d)$", v):
            raise ValueError("时间格式必须为HH:MM (例如: 23:00)")
        return v

import time
import aiohttp
import calendar
from PIL import Image
from io import BytesIO
from typing import Dict
from pathlib import Path

from .models import Player
from .data_source import BindData


async def _fetch_avatar(avatar_url: str, proxy: str = None) -> Image.Image:
    async with aiohttp.ClientSession() as session:
        async with session.get(avatar_url, proxy=proxy) as resp:
            if resp.status != 200:
                return Image.open(Path(__file__).parent / "res/unknown_avatar.jpg")
            return Image.open(BytesIO(await resp.read()))


async def fetch_avatar(
    player: Player, avatar_dir: Path, proxy: str = None
) -> Image.Image:
    if avatar_dir is not None:
        avatar_path = (
            avatar_dir / f"avatar_{player['steamid']}_{player['avatarhash']}.png"
        )

        if avatar_path.exists():
            avatar = Image.open(avatar_path)
        else:
            avatar = await _fetch_avatar(player["avatarfull"], proxy)

            avatar.save(avatar_path)
    else:
        avatar = await _fetch_avatar(player["avatarfull"], proxy)

    return avatar


def convert_player_name_to_nickname(data: Dict[str, str], parent_id: str, bind_data: BindData) -> Dict[str, str]:
    data["nickname"] = bind_data.get_by_steam_id(parent_id, data["steamid"])["nickname"]
    return data


async def simplize_steam_player_data(
    player: Player, proxy: str = None, avatar_dir: Path = None
) -> Dict[str, str]:
    avatar = await fetch_avatar(player, avatar_dir, proxy)

    if player["personastate"] == 0:
        if not player.get("lastlogoff"):
            status = "离线"
        else:
            time_logged_off = player["lastlogoff"]  # Unix timestamp
            time_to_now = calendar.timegm(time.gmtime()) - time_logged_off

            # 将时间转换为自然语言
            if time_to_now < 60:
                status = "上次在线 刚刚"
            elif time_to_now < 3600:
                status = f"上次在线 {time_to_now // 60} 分钟前"
            elif time_to_now < 86400:
                status = f"上次在线 {time_to_now // 3600} 小时前"
            elif time_to_now < 2592000:
                status = f"上次在线 {time_to_now // 86400} 天前"
            elif time_to_now < 31536000:
                status = f"上次在线 {time_to_now // 2592000} 个月前"
            else:
                status = f"上次在线 {time_to_now // 31536000} 年前"
    elif player["personastate"] in [1, 2, 4]:
        status = (
            "在线" if player.get("gameextrainfo") is None else player["gameextrainfo"]
        )
    elif player["personastate"] == 3:
        status = (
            "离开" if player.get("gameextrainfo") is None else player["gameextrainfo"]
        )
    elif player["personastate"] in [5, 6]:
        status = "在线"
    else:
        status = "未知"

    return {
        "steamid": player["steamid"],
        "avatar": avatar,
        "name": player["personaname"],
        "status": status,
        "personastate": player["personastate"],
    }


def image_to_bytes(image: Image.Image) -> bytes:
    with BytesIO() as bio:
        image.save(bio, format="PNG")
        return bio.getvalue()


def hex_to_rgb(hex_color: str):
    return tuple(int(hex_color[i : i + 2], 16) for i in (0, 2, 4))

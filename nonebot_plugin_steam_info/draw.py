import time
import aiohttp
import calendar
from io import BytesIO
from pathlib import Path
from typing import List, Dict
from PIL import Image, ImageDraw, ImageFont

from .models import Player


WIDTH = 400
PARENT_AVATAR_SIZE = 72
MEMBER_AVATAR_SIZE = 50

unknown_avatar_path = Path(__file__).parent / "res/unknown_avatar.jpg"
parent_status_path = Path(__file__).parent / "res/parent_status.png"
friends_search_path = Path(__file__).parent / "res/friends_search.png"
busy_path = Path(__file__).parent / "res/busy.png"
zzz_online_path = Path(__file__).parent / "res/zzz_online.png"
zzz_gaming_path = Path(__file__).parent / "res/zzz_gaming.png"

font_regular_path = (Path().cwd() / "fonts/MiSans-Regular.ttf").resolve().__str__()
font_light_path = (Path().cwd() / "fonts/MiSans-Light.ttf").resolve().__str__()
font_bold_path = (Path().cwd() / "fonts/MiSans-Bold.ttf").resolve().__str__()


def check_font():
    if not Path(font_regular_path).exists():
        raise FileNotFoundError(f"Font file {font_regular_path} not found.")
    if not Path(font_light_path).exists():
        raise FileNotFoundError(f"Font file {font_light_path} not found.")
    if not Path(font_bold_path).exists():
        raise FileNotFoundError(f"Font file {font_bold_path} not found.")


async def fetch_avatar(avatar_url: str, proxy: str = None) -> Image.Image:
    async with aiohttp.ClientSession() as session:
        async with session.get(avatar_url, proxy=proxy) as resp:
            if resp.status != 200:
                return Image.open(unknown_avatar_path)
            return Image.open(BytesIO(await resp.read()))


async def simplize_steam_player_data(
    player: Player, proxy: str = None, avatar_dir: Path = None
) -> Dict[str, str]:
    if avatar_dir is not None:
        avatar_path = avatar_dir / f"avatar_{player['steamid']}.png"

        if avatar_path.exists():
            avatar = Image.open(avatar_path)
        else:
            avatar = await fetch_avatar(player["avatarfull"], proxy)

            avatar.save(avatar_path)
    else:
        avatar = await fetch_avatar(player["avatarfull"], proxy)

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
            "在线"
            if player.get("gameextrainfo") is None
            else player["gameextrainfo"]
        )
    elif player["personastate"] == 3:
        status = (
            "离开"
            if player.get("gameextrainfo") is None
            else player["gameextrainfo"]
        )
    elif player["personastate"] in [5, 6]:
        status = "在线"
    else:
        status = "未知"

    return {
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


personastate_colors = {
    0: (hex_to_rgb("969697"), hex_to_rgb("656565")),
    1: (hex_to_rgb("6dcef5"), hex_to_rgb("4c91ac")),
    2: (hex_to_rgb("6dcef5"), hex_to_rgb("4c91ac")),
    3: (hex_to_rgb("45778e"), hex_to_rgb("365969")),
    4: (hex_to_rgb("6dcef5"), hex_to_rgb("4c91ac")),
    5: (hex_to_rgb("6dcef5"), hex_to_rgb("4c91ac")),
    6: (hex_to_rgb("6dcef5"), hex_to_rgb("4c91ac")),
}


def draw_parent_status(parent_avatar: Image.Image, parent_name: str) -> Image.Image:
    parent_avatar = parent_avatar.resize(
        (PARENT_AVATAR_SIZE, PARENT_AVATAR_SIZE), Image.BICUBIC
    )

    canvas = Image.open(parent_status_path).resize((WIDTH, 120), Image.BICUBIC)

    draw = ImageDraw.Draw(canvas)

    # 在左下角 (16, 16) 处绘制头像
    avatar_height = 120 - 16 - PARENT_AVATAR_SIZE
    canvas.paste(parent_avatar, (16, avatar_height))

    # 绘制名称
    draw.text(
        (16 + PARENT_AVATAR_SIZE + 16, avatar_height + 12),
        parent_name,
        font=ImageFont.truetype(font_bold_path, 20),
        fill=hex_to_rgb("6dcff6"),
    )

    # 绘制状态
    draw.text(
        (16 + PARENT_AVATAR_SIZE + 16, avatar_height + 20 + 16),
        "在线",
        font=ImageFont.truetype(font_light_path, 18),
        fill=hex_to_rgb("4c91ac"),
    )

    return canvas


def draw_friends_search() -> Image.Image:
    canvas = Image.new("RGB", (WIDTH, 50), hex_to_rgb("434953"))

    friends_search = Image.open(friends_search_path)

    canvas.paste(friends_search, (WIDTH - friends_search.width, 0))

    draw = ImageDraw.Draw(canvas)

    draw.text(
        (24, 10),
        "好友",
        hex_to_rgb("b7ccd5"),
        font=ImageFont.truetype(font_regular_path, 20),
    )

    return canvas


def draw_friend_status(
    friend_avatar: Image.Image, friend_name: str, status: str, personastate: int
) -> Image.Image:
    friend_avatar = friend_avatar.resize(
        (MEMBER_AVATAR_SIZE, MEMBER_AVATAR_SIZE), Image.BICUBIC
    )

    canvas = Image.new("RGB", (WIDTH, 64), hex_to_rgb("1e2024"))

    draw = ImageDraw.Draw(canvas)

    if personastate == 2:
        # 忙碌 加上一个忙碌图标
        canvas = draw_friend_status(friend_avatar, friend_name, status, 1)
        draw = ImageDraw.Draw(canvas)

        busy = Image.open(busy_path)

        name_width = int(
            draw.textlength(friend_name, font=ImageFont.truetype(font_bold_path, 20))
        )

        canvas.paste(busy, (22 + MEMBER_AVATAR_SIZE + 16 + name_width + 4, 18))

        return canvas

    if personastate == 4:
        # 打盹 加上一个 ZZZ
        canvas = draw_friend_status(friend_avatar, friend_name, status, 1)
        draw = ImageDraw.Draw(canvas)

        zzz = Image.open(zzz_online_path if status == "在线" else zzz_gaming_path)

        name_width = int(
            draw.textlength(friend_name, font=ImageFont.truetype(font_bold_path, 20))
        )

        canvas.paste(zzz, (22 + MEMBER_AVATAR_SIZE + 16 + name_width + 8, 18))

        return canvas

    # 绘制头像
    canvas.paste(friend_avatar, (22, 8))

    if status != "在线" and personastate == 1:
        fill = (hex_to_rgb("e3ffc2"), hex_to_rgb("8ebe56"))
    elif status != "离开" and personastate == 3:
        fill = (hex_to_rgb("e3ffc2"), hex_to_rgb("8ebe56"))
    else:
        fill = personastate_colors[personastate]

    # 绘制名称
    draw.text(
        (22 + MEMBER_AVATAR_SIZE + 18, 12),
        friend_name,
        font=ImageFont.truetype(font_bold_path, 20),
        fill=fill[0],
    )

    # 绘制状态
    draw.text(
        (22 + MEMBER_AVATAR_SIZE + 16, 36),
        status,
        font=ImageFont.truetype(font_regular_path, 18),
        fill=fill[1],
    )

    return canvas


def draw_gaming_friends_status(data: List[Dict[str, str]]) -> Image.Image:
    canvas = Image.new(
        "RGB",
        (WIDTH, 64 + (MEMBER_AVATAR_SIZE + 16) * len(data) + 16),
        hex_to_rgb("1e2024"),
    )

    draw = ImageDraw.Draw(canvas)

    # 绘制标题
    draw.text(
        (22, 22),
        "游戏中",
        hex_to_rgb("c5d6d4"),
        font=ImageFont.truetype(font_regular_path, 22),
    )

    # 绘制好友头像和名称
    friends_status_list = [
        draw_friend_status(d["avatar"], d["name"], d["status"], d["personastate"])
        for d in data
    ]

    # 拼接好友头像和名称
    for i, friend_status in enumerate(friends_status_list):
        canvas.paste(friend_status, (0, 64 + (MEMBER_AVATAR_SIZE + 16) * i))

    return canvas


def draw_online_friends_status(data: List[Dict[str, str]]) -> Image.Image:
    canvas = Image.new(
        "RGB",
        (WIDTH, 64 + (MEMBER_AVATAR_SIZE + 16) * len(data) + 16),
        hex_to_rgb("1e2024"),
    )

    draw = ImageDraw.Draw(canvas)

    # 绘制标题
    draw.text(
        (22, 22),
        "在线好友",
        hex_to_rgb("c5d6d4"),
        font=ImageFont.truetype(font_regular_path, 22),
    )

    # 绘制在线人数
    draw.text(
        (115, 25),
        f"({len(data)})",
        hex_to_rgb("67665c"),
        font=ImageFont.truetype(font_regular_path, 18),
    )

    # 绘制好友头像和名称
    friends_status_list = [
        draw_friend_status(d["avatar"], d["name"], d["status"], d["personastate"])
        for d in data
    ]

    # 拼接好友头像和名称
    for i, friend_status in enumerate(friends_status_list):
        canvas.paste(friend_status, (0, 64 + (MEMBER_AVATAR_SIZE + 16) * i))

    return canvas


def draw_offline_friends_status(data: List[Dict[str, str]]) -> Image.Image:
    canvas = Image.new(
        "RGB",
        (WIDTH, 64 + (MEMBER_AVATAR_SIZE + 16) * len(data) + 16),
        hex_to_rgb("1e2024"),
    )

    draw = ImageDraw.Draw(canvas)

    # 绘制标题
    draw.text(
        (22, 22),
        "离线",
        hex_to_rgb("c5d6d4"),
        font=ImageFont.truetype(font_regular_path, 22),
    )

    # 绘制离线人数
    draw.text(
        (72, 25),
        f"({len(data)})",
        hex_to_rgb("67665c"),
        font=ImageFont.truetype(font_regular_path, 18),
    )

    # 绘制好友头像和名称
    friends_status_list = [
        draw_friend_status(d["avatar"], d["name"], d["status"], d["personastate"])
        for d in data
    ]

    # 拼接好友头像和名称
    for i, friend_status in enumerate(friends_status_list):
        canvas.paste(friend_status, (0, 64 + (MEMBER_AVATAR_SIZE + 16) * i))

    return canvas


def draw_friends_status(
    parent_avatar: Image.Image, parent_name: str, data: List[Dict[str, str]]
):
    data.sort(key=lambda x: x["personastate"])

    parent_status = draw_parent_status(parent_avatar, parent_name)
    friends_search = draw_friends_search()

    status_images: List[Image.Image] = []
    height = parent_status.height + friends_search.height

    gaming_data = [
        d
        for d in data
        if (d["personastate"] == 1 and d["status"] != "在线")
        or (d["personastate"] == 3 and d["status"] != "离开")
        or (d["personastate"] == 4 and d["status"] != "在线")
    ]

    if gaming_data:
        status_images.append(draw_gaming_friends_status(gaming_data))
        height += status_images[-1].height

    online_data = [
        d
        for d in data
        if (d["personastate"] == 1 and d["status"] == "在线")
        or (d["personastate"] == 3 and d["status"] == "离开")
        or (d["personastate"] == 4 and d["status"] == "在线")
        or (d["personastate"] in [2, 5, 6])
    ]
    # 按 1, 2, 4, 5, 6, 3 的顺序排序
    online_data.sort(key=lambda x: (7 if x["personastate"] == 3 else x["personastate"]))

    if online_data:
        status_images.append(draw_online_friends_status(online_data))
        height += status_images[-1].height

    offline_data = [d for d in data if d["personastate"] == 0]
    if offline_data:
        status_images.append(draw_offline_friends_status(offline_data))
        height += status_images[-1].height

    # 拼合图片
    canvas = Image.new("RGB", (WIDTH, height), hex_to_rgb("1e2024"))
    draw = ImageDraw.Draw(canvas)

    canvas.paste(parent_status, (0, 0))
    canvas.paste(friends_search, (0, parent_status.height))

    y = parent_status.height + friends_search.height

    for i, status_image in enumerate(status_images):
        canvas.paste(status_image, (0, y))
        y += status_image.height

        # 绘制分割线
        if i != len(status_images) - 1:
            draw.rectangle([0, y - 1, WIDTH, y], fill=hex_to_rgb("333439"))

    return canvas

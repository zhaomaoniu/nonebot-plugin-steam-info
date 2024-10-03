import numpy as np
from io import BytesIO
from pathlib import Path
from typing import List, Dict, Tuple
from colorsys import rgb_to_hsv, hsv_to_rgb
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance

from .utils import hex_to_rgb
from .models import DrawPlayerStatusData, Achievements


WIDTH = 400
PARENT_AVATAR_SIZE = 72
MEMBER_AVATAR_SIZE = 50

unknown_avatar_path = Path(__file__).parent / "res/unknown_avatar.jpg"
parent_status_path = Path(__file__).parent / "res/parent_status.png"
friends_search_path = Path(__file__).parent / "res/friends_search.png"
busy_path = Path(__file__).parent / "res/busy.png"
zzz_online_path = Path(__file__).parent / "res/zzz_online.png"
zzz_gaming_path = Path(__file__).parent / "res/zzz_gaming.png"
gaming_path = Path(__file__).parent / "res/gaming.png"

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


personastate_colors = {
    0: (hex_to_rgb("969697"), hex_to_rgb("656565")),
    1: (hex_to_rgb("6dcef5"), hex_to_rgb("4c91ac")),
    2: (hex_to_rgb("6dcef5"), hex_to_rgb("4c91ac")),
    3: (hex_to_rgb("45778e"), hex_to_rgb("365969")),
    4: (hex_to_rgb("6dcef5"), hex_to_rgb("4c91ac")),
    5: (hex_to_rgb("6dcef5"), hex_to_rgb("4c91ac")),
    6: (hex_to_rgb("6dcef5"), hex_to_rgb("4c91ac")),
}


def vertically_concatenate_images(images: List[Image.Image]) -> Image.Image:
    widths, heights = zip(*(i.size for i in images))
    total_width = max(widths)
    total_height = sum(heights)

    new_image = Image.new("RGB", (total_width, total_height))

    y_offset = 0
    for image in images:
        new_image.paste(image, (0, y_offset))
        y_offset += image.size[1]

    return new_image


def draw_start_gaming(
    avatar: Image.Image, friend_name: str, game_name: str, nickname: str = None
):
    canvas = Image.open(gaming_path)
    canvas.paste(avatar.resize((66, 66), Image.BICUBIC), (15, 20))

    # 绘制名称
    draw = ImageDraw.Draw(canvas)
    draw.text(
        (104, 14),
        f"{friend_name} ({nickname})" if nickname is not None else friend_name,
        font=ImageFont.truetype(font_regular_path, 19),
        fill=hex_to_rgb("e3ffc2"),
    )

    # 绘制"正在玩"
    draw.text(
        (103, 42),
        "正在玩",
        font=ImageFont.truetype(font_regular_path, 17),
        fill=hex_to_rgb("969696"),
    )

    # 绘制游戏名称
    draw.text(
        (104, 66),
        game_name,
        font=ImageFont.truetype(font_bold_path, 14),
        fill=hex_to_rgb("91c257"),
    )

    return canvas


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
    friend_avatar: Image.Image,
    friend_name: str,
    status: str,
    personastate: int,
    nickname: str = None,
) -> Image.Image:
    friend_avatar = friend_avatar.resize(
        (MEMBER_AVATAR_SIZE, MEMBER_AVATAR_SIZE), Image.BICUBIC
    )

    canvas = Image.new("RGB", (WIDTH, 64), hex_to_rgb("1e2024"))

    draw = ImageDraw.Draw(canvas)

    display_name = (
        f"{friend_name} ({nickname})" if nickname is not None else friend_name
    )

    if personastate == 2:
        # 忙碌 加上一个忙碌图标
        canvas = draw_friend_status(friend_avatar, friend_name, status, 1, nickname)
        draw = ImageDraw.Draw(canvas)

        busy = Image.open(busy_path)

        name_width = int(
            draw.textlength(display_name, font=ImageFont.truetype(font_bold_path, 20))
        )

        canvas.paste(busy, (22 + MEMBER_AVATAR_SIZE + 16 + name_width + 4, 18))

        return canvas

    if personastate == 4:
        # 打盹 加上一个 ZZZ
        canvas = draw_friend_status(friend_avatar, friend_name, status, 1, nickname)
        draw = ImageDraw.Draw(canvas)

        zzz = Image.open(zzz_online_path if status == "在线" else zzz_gaming_path)

        name_width = int(
            draw.textlength(display_name, font=ImageFont.truetype(font_bold_path, 20))
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
        display_name,
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
    # 排序数据，按照游戏名称字母表顺序排序
    data.sort(key=lambda x: x["status"])

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
        draw_friend_status(
            d["avatar"], d["name"], d["status"], d["personastate"], d["nickname"]
        )
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
        draw_friend_status(
            d["avatar"], d["name"], d["status"], d["personastate"], d["nickname"]
        )
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
        draw_friend_status(
            d["avatar"], d["name"], d["status"], d["personastate"], d["nickname"]
        )
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


def get_average_color(image: Image.Image) -> tuple[int, int, int]:
    """获取图片的平均颜色"""
    image_np = np.array(image)
    average_color = image_np.mean(axis=(0, 1)).astype(int)
    return tuple(average_color)


def split_image(
    image: Image.Image, rows: int, cols: int
) -> tuple[list[Image.Image], int, int]:
    """将图片分割为rows * cols份"""
    width, height = image.size
    piece_width = width // cols
    piece_height = height // rows
    pieces = []

    for r in range(rows):
        for c in range(cols):
            box = (
                c * piece_width,
                r * piece_height,
                (c + 1) * piece_width,
                (r + 1) * piece_height,
            )
            piece = image.crop(box)
            pieces.append(piece)

    return pieces, piece_width, piece_height


def recolor_image(image: Image.Image, rows: int, cols: int) -> Image.Image:
    """分片图片，提取平均颜色后拼接"""
    total_average_color = get_average_color(image)  # 获取整体平均颜色
    pieces, piece_width, piece_height = split_image(image, rows, cols)

    diameter = min(pieces[0].size)  # 以最小边为直径
    radius = diameter // 2
    new_image = Image.new("RGB", image.size, total_average_color)

    for i, piece in enumerate(pieces):
        average_color = get_average_color(piece)  # 获取每片的平均颜色

        # 计算放置的位置
        row, col = divmod(i, cols)
        x = col * piece_width + piece_width // 2
        y = row * piece_height + piece_height // 2

        # 画圆
        circle = Image.new("RGBA", (piece_width, piece_height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(circle)
        draw.ellipse((0, 0, piece_width, piece_height), fill=average_color)

        # 将圆形图片粘贴到新图片上
        new_image.paste(circle, (x - radius, y - radius), circle)

    new_image = new_image.filter(ImageFilter.SMOOTH)
    new_image = new_image.filter(ImageFilter.GaussianBlur(50))

    return new_image


def create_gradient_image(
    size: Tuple[int, int], color1: Tuple[int, int, int], color2: Tuple[int, int, int]
) -> Image.Image:
    """创建渐变图片"""
    # 创建一个渐变的线性空间
    gradient_array = np.linspace(color1, color2, size[0])

    # 将渐变数组的形状调整为 (height, width, 3)
    gradient_image = np.tile(gradient_array, (size[1], 1, 1)).astype(np.uint8)

    return Image.fromarray(gradient_image, "RGBA")


def random_color_offset(
    color: Tuple[int, int, int], offset: int
) -> Tuple[int, int, int]:
    return tuple(
        min(255, max(0, c + np.random.randint(-offset, offset + 1))) for c in color
    )


def get_brightest_and_darkest_color(
    image: Image.Image,
    saturation_threshold: int = 100,
    hue_difference_threshold: int = 30,
) -> Tuple[Tuple[int, int, int], Tuple[int, int, int]]:
    """获取图片最亮和最暗的颜色"""
    # 将RGB图像转换为HSV
    img_hsv = np.array(image.convert("HSV"))

    # 设定一个阈值来定义“鲜艳的颜色”，例如饱和度大于150
    vivid_mask = img_hsv[..., 1] > saturation_threshold

    # 获取饱和度较高（鲜艳）的像素索引
    vivid_pixels = img_hsv[vivid_mask]

    if len(vivid_pixels) < 10:
        return get_brightest_and_darkest_color(image, saturation_threshold - 10)

    # 在鲜艳的像素中，根据亮度（V通道）找到最亮和最暗的颜色
    brightest_pixel = vivid_pixels[np.argmax(vivid_pixels[..., 2])]
    darkest_pixel = vivid_pixels[np.argmin(vivid_pixels[..., 2])]

    # 获取最亮和最暗的颜色的色相差异
    hue_difference = abs(int(brightest_pixel[0]) - int(darkest_pixel[0]))

    # 如果色相差异过小，则尝试寻找新的最暗颜色，直到色相差异大于设定阈值
    if hue_difference < hue_difference_threshold:
        possible_dark_pixels = vivid_pixels[vivid_pixels[..., 0] != brightest_pixel[0]]
        if len(possible_dark_pixels) > 0:
            darkest_pixel = possible_dark_pixels[
                np.argmin(possible_dark_pixels[..., 2])
            ]

    # 将最亮和最暗的像素从HSV转回RGB
    brightest_color = (
        Image.fromarray(np.uint8([[brightest_pixel]]), "HSV")
        .convert("RGB")
        .getpixel((0, 0))
    )
    darkest_color = (
        Image.fromarray(np.uint8([[darkest_pixel]]), "HSV")
        .convert("RGB")
        .getpixel((0, 0))
    )

    return brightest_color, darkest_color


def draw_game_info(
    header: Image.Image,
    game_name: str,
    game_time: str,
    last_play_time: str,
    achievements: List[Achievements],
    completed_achievement_number: int,
    total_achievement_number: int,
    achievement_color: Tuple[int, int, int],
) -> Image.Image:
    bg = Image.new("RGBA", (880, 110 + 64 + 10), (0, 0, 0, 110))
    header = header.resize((229, 86), Image.BICUBIC)
    bg.paste(header, (10, 110 // 2 - header.height // 2))

    draw = ImageDraw.Draw(bg)

    # 画游戏名
    draw.text(
        (260, 10),
        game_name,
        font=ImageFont.truetype(font_regular_path, 26),
        fill=(255, 255, 255),
    )

    # 画最后游玩时间
    font = ImageFont.truetype(font_light_path, 22)
    display_text = f"最后运行日期：{last_play_time}"
    draw.text(
        (int(bg.width - font.getlength(display_text)) - 10, 75),
        display_text,
        font=font,
        fill=(150, 150, 150),
    )

    # 画游戏时间
    font = ImageFont.truetype(font_light_path, 22)
    display_text = f"总时数 {game_time}"
    draw.text(
        (int(bg.width - font.getlength(display_text)) - 10, 50),
        display_text,
        font=font,
        fill=(150, 150, 150),
    )

    if completed_achievement_number is None or total_achievement_number is None:
        return bg.crop((0, 0, bg.width, 110))

    # 画成就  + 64 + 10
    achievement_bg = Image.new("RGBA", (860, 64), achievement_color)
    draw_achievement = ImageDraw.Draw(achievement_bg)

    # 画成就进度
    font = ImageFont.truetype(font_light_path, 18)
    x = 14
    draw_achievement.text(
        (x, 20),
        "成就进度",
        font=font,
        fill=(255, 255, 255, 255),
    )
    x += font.getlength("成就进度") + 10
    draw_achievement.text(
        (int(x), 20),
        f"{completed_achievement_number} / {total_achievement_number}",
        font=font,
        fill=(130, 130, 130),
    )
    x += (
        font.getlength(f"{completed_achievement_number} / {total_achievement_number}")
        + 10
    )
    progress_bar = create_progress_bar(
        completed_achievement_number / total_achievement_number, achievement_color
    )
    achievement_bg.paste(progress_bar, (int(x), 24), progress_bar)

    # 画成就图标
    x = 860 - 48 * 6 - 10 * 6
    for achievement in achievements:
        achievement_image = Image.open(BytesIO(achievement["image"])).resize((48, 48))
        achievement_bg.paste(achievement_image, (x, 8))
        x += 48 + 10

    if completed_achievement_number > 6:
        font = ImageFont.truetype(font_regular_path, 22)
        display_text = f"+{completed_achievement_number - 5}"
        draw_achievement.rectangle((x, 8, x + 48, 56), fill=(34, 34, 34))
        draw_achievement.text(
            (x + 24 - font.getlength(display_text) // 2, 18),
            display_text,
            font=font,
            fill=(255, 255, 255),
        )

    bg.paste(achievement_bg, (10, 110), achievement_bg)
    return bg


def draw_player_status(
    player_bg: Image.Image,
    player_avatar: Image.Image,
    player_name: str,
    player_id: str,
    player_description: str,
    player_last_two_weeks_time: str,  # e.g. 10.2 小时
    player_games: List[DrawPlayerStatusData],
):
    if isinstance(player_bg, bytes):
        player_bg = Image.open(BytesIO(player_bg))
    if isinstance(player_avatar, bytes):
        player_avatar = Image.open(BytesIO(player_avatar))

    bg = recolor_image(
        player_bg.crop(
            (
                (player_bg.width - 960) // 2,
                0,
                (player_bg.width + 960) // 2,
                player_bg.height,
            )
        ),
        10,
        10,
    )
    # 调暗背景
    enhancer = ImageEnhance.Brightness(bg)
    bg = enhancer.enhance(0.7)
    # bg.size = (960, 1020)
    player_avatar = player_avatar.resize((200, 200))
    bg.paste(player_avatar, (40, 40))

    draw = ImageDraw.Draw(bg)

    # 画头像外框
    draw.rectangle((40, 40, 240, 240), outline=(83, 164, 196), width=3)

    # 画昵称
    draw.text(
        (280, 48),
        player_name,
        font=ImageFont.truetype(font_light_path, 40),
        fill=(255, 255, 255),
    )

    # 画ID
    draw.text(
        (280, 100),
        f"好友代码: {player_id}",
        font=ImageFont.truetype(font_regular_path, 19),
        fill=(191, 191, 191),
    )

    # 画简介
    line_width = 0
    offset = 0
    line = ""
    for idx, char in enumerate(player_description):
        line += char
        line_width += ImageFont.truetype(font_light_path, 22).getlength(char)
        if line_width > 640 or idx == len(player_description) - 1 or char == "\n":
            draw.text(
                (280, 132 + offset),
                line,
                font=ImageFont.truetype(font_light_path, 22),
                fill=(255, 255, 255),
            )
            line = ""
            offset += 25
            line_width = 0
        if offset >= 25 * 4:
            break

    # 画游戏

    brightest_color, darkest_color = get_brightest_and_darkest_color(player_bg)
    brightest_color = tuple(map(lambda x: x - 30 if x >= 30 else 0, brightest_color))
    darkest_color = tuple(
        map(lambda x: x + 30 if x <= 255 - 30 else 255, darkest_color)
    )
    brightest_color = (brightest_color[0], brightest_color[1], brightest_color[2], 128)
    brightest_color = random_color_offset(brightest_color, 20)
    darkest_color = (darkest_color[0], darkest_color[1], darkest_color[2], 128)
    darkest_color = random_color_offset(darkest_color, 20)

    # 画游戏信息
    hsv_achievement_color = rgb_to_hsv(*brightest_color[:3])
    achievement_color = tuple(
        map(
            int,
            hsv_to_rgb(
                hsv_achievement_color[0],
                hsv_achievement_color[1] * 0.85,
                hsv_achievement_color[2] * 0.6,
            ),
        )
    )
    game_images: List[Image.Image] = []
    for idx, game in enumerate(player_games):
        game_image = Image.open(BytesIO(game["game_header"]))
        game_info = draw_game_info(
            game_image,
            game["game_name"],
            game["game_time"],
            game["last_play_time"],
            game["achievements"],
            game["completed_achievement_number"],
            game["total_achievement_number"],
            achievement_color,
        )
        game_images.append(game_info)

    # 画半透明黑色背景
    bg_game = Image.new(
        "RGBA", (920, 106 + sum([game_image.height + 26 for game_image in game_images]))
    )
    draw_game = ImageDraw.Draw(bg_game)
    draw_game.rectangle(
        (
            0,
            0,
            920,
            bg_game.height,
        ),
        fill=(0, 0, 0, 120),
    )
    bg.paste(bg_game, (20, 272), bg_game)

    # 画渐变条
    gradient = create_gradient_image((920, 50), brightest_color, darkest_color)
    bg.paste(gradient, (20, 272), gradient)

    # 画渐变条的文字：最新动态，最近游戏
    draw.text(
        (34, 279),
        "最新动态",
        font=ImageFont.truetype(font_light_path, 26),
        fill=(255, 255, 255),
    )
    if player_last_two_weeks_time is not None:
        width = ImageFont.truetype(font_light_path, 26).getlength(
            player_last_two_weeks_time
        )
        draw.text(
            (960 - width - 34, 279),
            player_last_two_weeks_time,
            font=ImageFont.truetype(font_light_path, 26),
            fill=(255, 255, 255),
        )

    y = 350
    for idx, game_image in enumerate(game_images):
        bg.paste(
            game_image,
            ((920 - game_image.width) // 2 + 20, y),
            game_image.convert("RGBA"),
        )
        y += game_image.height + 26

    player_bg.paste(bg, ((player_bg.width - 960) // 2, 0), bg.convert("RGBA"))

    return player_bg


def create_vertical_gradient_rect(width, height, start_color, end_color):
    """
    创建一个在竖直方向上渐变的矩形图像.

    Args:
        width (int): 矩形的宽度 (以像素为单位).
        height (int): 矩形的高度 (以像素为单位).
        start_color (tuple): 起始颜色，格式为 (R, G, B)，每个值范围为 0-255.
        end_color (tuple): 结束颜色，格式为 (R, G, B)，每个值范围为 0-255.

    Returns:
        Image: PIL Image 对象，表示生成的渐变矩形.
    """
    # 确保颜色不超过 0-255 的范围
    start_color = tuple(max(0, min(255, c)) for c in start_color)
    end_color = tuple(max(0, min(255, c)) for c in end_color)

    # 使用 NumPy 创建一个线性渐变数组
    gradient_array = np.linspace(start_color, end_color, num=height, dtype=np.uint8)
    gradient_array = np.repeat(gradient_array, width, axis=0).reshape(
        (height, width, 3)
    )

    # 使用 Pillow 创建图像并填充颜色
    image = Image.fromarray(gradient_array)
    return image


def rounded_rectangle(
    image: Image.Image,
    radius: int,
    border=False,
    border_width=0,
    border_color=(0, 0, 0),
):
    """
    将给定的Image.Image对象切割为圆角矩形。

    Args:
        image: 一个PIL Image对象。
        radius: 圆角半径，单位为像素。
        border: 是否需要边框，默认为False。
        border_width: 边框宽度，单位为像素，默认为0。
        border_color: 边框颜色，RGB元组，默认为黑色(0, 0, 0)。

    Returns:
        一个PIL Image对象，表示切割后的圆角矩形图像。
    """

    width, height = image.size

    image_ = Image.new("RGBA", (width + 1, height + 1), (0, 0, 0, 0))
    image_.paste(image, (0, 0), image.convert("RGBA"))

    # 创建一个圆角矩形的遮罩
    result = Image.new("RGBA", (width + 1, height + 1), (0, 0, 0, 0))
    mask = Image.new("L", (width + 1, height + 1), 0)
    draw = ImageDraw.Draw(mask)
    image_draw = ImageDraw.Draw(result)

    # 绘制圆角矩形
    draw.rounded_rectangle((0, 0, width, height), radius=radius, fill=255)

    # 应用遮罩到原始图像
    result.paste(image_, (0, 0), mask)

    # 添加边框 (如果需要)
    if border:
        image_draw.rounded_rectangle(
            (0, 0, width, height),
            radius=radius,
            outline=border_color,
            width=border_width,
        )

    return result


def create_progress_bar(
    progress: float, color: Tuple[int, int, int], width=186, height=16
):
    color_hsv = rgb_to_hsv(*color)

    # 外条
    bar_color = tuple(
        map(int, hsv_to_rgb(color_hsv[0], color_hsv[1], color_hsv[2] * 0.8))
    )
    border_color = tuple(map(lambda x: max(x - 20, 0), color))
    border_image = rounded_rectangle(
        Image.new("RGBA", (width, height), bar_color),
        8,
        border=True,
        border_width=1,
        border_color=border_color,
    )

    # 内条
    bar_color_top = tuple(
        map(int, hsv_to_rgb(color_hsv[0], color_hsv[1] / 2, color_hsv[2] * 5 / 2))
    )
    bar_color_bottem = tuple(
        map(int, hsv_to_rgb(color_hsv[0], color_hsv[1] / 2, color_hsv[2]))
    )

    bar_image = create_vertical_gradient_rect(
        int(width * progress), height - 4, bar_color_top, bar_color_bottem
    )
    bar_image = rounded_rectangle(bar_image, 6)

    # 合并
    border_image.paste(bar_image, (3, 2), bar_image)

    return border_image

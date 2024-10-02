from io import BytesIO
from pathlib import Path
from typing import Tuple
from PIL import Image, ImageFilter, ImageEnhance, ImageDraw, ImageFont

try:
    from .models import DrawPlayerStatusData  # type: ignore
except:

    class DrawPlayerStatusData:
        pass


font_regular_path = "D://assets/MiSans-Regular.ttf"
font_light_path = "D://assets/MiSans-Light.ttf"
font_bold_path = "D://assets/MiSans-Bold.ttf"


import numpy as np


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
) -> Tuple[Tuple[int, int, int], Tuple[int, int, int]]:
    """获取图片最亮和最暗的颜色"""
    image_np = np.array(image)
    image_np = image_np.reshape(-1, 3)
    # 计算每个像素的亮度
    brightness = np.sum(image_np, axis=1)

    # 找到最亮和最暗的颜色
    brightest_color = image_np[np.argmax(brightness)]
    darkest_color = image_np[np.argmin(brightness)]

    return tuple(brightest_color), tuple(darkest_color)


def draw_game_info(
    header: Image.Image,
    game_name: str,
    game_time: str,
    last_play_time: str,
) -> Image.Image:
    bg = Image.new("RGBA", (790, 110), (0, 0, 0, 60))
    bg.paste(header, (10, 10))


def draw_player_status(
    player_bg: Image.Image,
    player_avatar: Image.Image,
    player_name: str,
    player_id: str,
    player_description: str,
    player_last_two_weeks_time: str, # e.g. 10.2 小时
    player_games: list[DrawPlayerStatusData],
):
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
        font=ImageFont.truetype(font_regular_path, 22),
        fill=(191, 191, 191),
    )

    # 画简介
    line_width = 0
    offset = 0
    line = ""
    for idx, char in enumerate(player_description):
        line += char
        line_width += ImageFont.truetype(font_light_path, 26).getlength(char)
        if line_width > 640 or idx == len(player_description) - 1 or char == "\n":
            draw.text(
                (280, 132 + offset),
                line,
                font=ImageFont.truetype(font_light_path, 26),
                fill=(255, 255, 255),
            )
            line = ""
            offset += 32
            line_width = 0
        if offset >= 32 * 3:
            break

    # 画游戏
    # 画半透明黑色背景
    bg_game = Image.new("RGBA", (920, 960))
    draw_game = ImageDraw.Draw(bg_game)
    draw_game.rectangle((0, 0, 920, 898), fill=(0, 0, 0, 120))
    bg.paste(bg_game, (20, 272), bg_game)

    # 画渐变条
    brightest_color, darkest_color = get_brightest_and_darkest_color(player_bg)
    brightest_color = tuple(map(lambda x: x - 30, brightest_color))
    darkest_color = tuple(map(lambda x: x + 30, darkest_color))
    brightest_color = (brightest_color[0], brightest_color[1], brightest_color[2], 128)
    brightest_color = random_color_offset(brightest_color, 20)
    darkest_color = (darkest_color[0], darkest_color[1], darkest_color[2], 128)
    darkest_color = random_color_offset(darkest_color, 20)
    gradient = create_gradient_image((920, 50), brightest_color, darkest_color)
    bg.paste(gradient, (20, 272), gradient)

    # 画渐变条的文字：最新动态，最近游戏
    draw.text(
        (34, 279),
        "最新动态",
        font=ImageFont.truetype(font_light_path, 26),
        fill=(255, 255, 255),
    )
    display_text = f"{player_last_two_weeks_time}（过去 2 周）"
    width = ImageFont.truetype(font_light_path, 26).getlength(display_text)
    draw.text(
        (960 - width - 34, 279),
        display_text,
        font=ImageFont.truetype(font_light_path, 26),
        fill=(255, 255, 255),
    )

    # 画游戏信息

    player_bg.paste(bg, (480, 0))

    return player_bg


if __name__ == "__main__":
    draw_player_status(
        Image.open(r"D:\assets\murasame.png"),
        Image.open(r"D:\assets\3ade30f61c3d2cc0b8c80aaf567b573cd022c405_full.jpg"),
        "zhaomaoniu",
        "1174772451",
        "風が雨が激しくても\n思いだすんだ 僕らを照らす光があるよ\n今日もいっぱい\n明日もいっぱい 力を出しきってみるよ",
        "15.5 小时",
        [
            {
                "game_name": "Game1",
                "game_time": "10.2 小时",
                "last_play_time": "10 月 2 日",
                "game_header": Path(
                    r"D:\assets\capsule_184x69_schinese.jpg"
                ).read_bytes(),
            }
        ],
    ).show()

    # recolor_image(
    #     Image.open(r"D:\assets\murasame.png").crop(
    #         (
    #             (1920 - 960) // 2,
    #             0,
    #             (1920 + 960) // 2,
    #             1200,
    #         )
    #     ),
    #     10,
    #     10,
    # ).show()

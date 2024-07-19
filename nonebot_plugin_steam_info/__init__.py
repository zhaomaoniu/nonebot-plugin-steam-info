import time
import aiohttp
import nonebot
from io import BytesIO
from pathlib import Path
from nonebot.log import logger
from PIL import Image as PILImage
from nonebot.params import Depends
from nonebot.params import CommandArg
from nonebot import on_command, require
from typing import Union, Optional, List, Dict
from nonebot.adapters import Message, Event, Bot
from nonebot.plugin import PluginMetadata, inherit_supported_adapters

require("nonebot_plugin_alconna")
require("nonebot_plugin_localstore")
require("nonebot_plugin_apscheduler")

import nonebot_plugin_localstore as store
from nonebot_plugin_apscheduler import scheduler
from nonebot_plugin_alconna import Text, Image, UniMessage, Target

from .config import Config
from .models import ProcessedPlayer
from .steam import get_steam_id, get_steam_users_info, STEAM_ID_OFFSET
from .data_source import BindData, SteamInfoData, ParentData, DisableParentData
from .draw import (
    check_font,
    draw_start_gaming,
    draw_friends_status,
    vertically_concatenate_images,
)
from .utils import (
    fetch_avatar,
    image_to_bytes,
    simplize_steam_player_data,
    convert_player_name_to_nickname,
)


__plugin_meta__ = PluginMetadata(
    name="Steam Info",
    description="播报绑定的 Steam 好友状态",
    usage="绑定 Steam ID: steambind [Steam ID 或 Steam好友代码]\n解绑 Steam ID: steamunbind\n查看 Steam ID: steaminfo\n查看 Steam 好友状态: steamcheck\n启用 Steam 播报: steamenable\n禁用 Steam 播报: steamdisable\n更新群信息: steamupdate\n设置玩家昵称: steamnickname [昵称]",
    type="application",
    homepage="https://github.com/zhaomaoniu/nonebot-plugin-steam-info",
    config=Config,
    supported_adapters=inherit_supported_adapters("nonebot_plugin_alconna"),
)


bind = on_command("steambind", aliases={"绑定steam"}, priority=10)
unbind = on_command("steamunbind", aliases={"解绑steam"}, priority=10)
info = on_command("steaminfo", aliases={"steam信息"}, priority=10)
check = on_command("steamcheck", aliases={"查看steam", "查steam"}, priority=10)
enable = on_command("steamenable", aliases={"启用steam"}, priority=10)
disable = on_command("steamdisable", aliases={"禁用steam"}, priority=10)
update_parent_info = on_command("steamupdate", aliases={"更新群信息"}, priority=10)
set_nickname = on_command("steamnickname", aliases={"steam昵称"}, priority=10)


if hasattr(nonebot, "get_plugin_config"):
    config = nonebot.get_plugin_config(Config)
else:
    from nonebot import get_driver

    config = Config.parse_obj(get_driver().config)


bind_data_path = store.get_data_file("nonebot_plugin_steam_info", "bind_data.json")
steam_info_data_path = store.get_data_file(
    "nonebot_plugin_steam_info", "steam_info.json"
)
parent_data_path = store.get_data_file("nonebot_plugin_steam_info", "parent_data.json")
disable_parent_data_path = store.get_data_file(
    "nonebot_plugin_steam_info", "disable_parent_data.json"
)
avatar_path = store.get_cache_dir("nonebot_plugin_steam_info")

bind_data = BindData(bind_data_path)
steam_info_data = SteamInfoData(steam_info_data_path)
parent_data = ParentData(parent_data_path)
disable_parent_data = DisableParentData(disable_parent_data_path)

try:
    check_font()
except FileNotFoundError as e:
    logger.error(
        f"{e}, nonebot_plugin_steam_info 无法使用，请参照 `https://github.com/zhaomaoniu/nonebot-plugin-steam-info` 配置字体文件"
    )


async def get_target(event: Event, bot: Bot) -> Optional[Target]:
    target = UniMessage.get_target(event, bot, bot.adapter.get_name())

    if target.private:
        # 不支持私聊消息
        return None

    return target


async def to_image_data(image: Image) -> Union[BytesIO, bytes]:
    if image.raw is not None:
        return image.raw

    if image.path is not None:
        return Path(image.path).read_bytes()

    if image.url is not None:
        async with aiohttp.ClientSession() as session:
            async with session.get(image.url) as resp:
                if resp.status != 200:
                    raise ValueError(f"无法获取图片数据: {resp.status}")
                return await resp.read()

    raise ValueError("无法获取图片数据")


async def broadcast_steam_info(
    parent_id: str,
    old_players: List[ProcessedPlayer],
    new_players: List[ProcessedPlayer],
):
    if disable_parent_data.is_disabled(parent_id):
        return None

    bot = nonebot.get_bot()

    play_data = steam_info_data.compare(old_players, new_players)

    msg = []
    for entry in play_data:
        player: ProcessedPlayer = entry["player"]
        old_player: ProcessedPlayer = entry.get("old_player")

        if entry["type"] == "start":
            msg.append(f"{player['personaname']} 开始玩 {player['gameextrainfo']} 了")
        elif entry["type"] == "stop":
            time_start = old_player["game_start_time"]
            time_stop = time.time()
            hours = int((time_stop - time_start) / 3600)
            minutes = int((time_stop - time_start) % 3600 / 60)
            time_str = (
                f"{hours} 小时 {minutes} 分钟" if hours > 0 else f"{minutes} 分钟"
            )
            msg.append(
                f"{player['personaname']} 玩了 {time_str} {old_player['gameextrainfo']} 后不玩了"
            )
        elif entry["type"] == "change":
            msg.append(
                f"{player['personaname']} 停止玩 {old_player['gameextrainfo']}，开始玩 {player['gameextrainfo']} 了"
            )
        elif entry["type"] == "error":
            f"出现错误！{player['personaname']}\nNew: {player.get('gameextrainfo')}\nOld: {old_player.get('gameextrainfo')}"
        else:
            logger.error(f"未知的播报类型: {entry['type']}")

    if msg == []:
        return None

    if config.steam_broadcast_type == "all":
        steam_status_data = [
            convert_player_name_to_nickname(
                (await simplize_steam_player_data(player, config.proxy, avatar_path)),
                parent_id,
                bind_data,
            )
            for player in new_players
        ]

        parent_avatar, parent_name = parent_data.get(parent_id)
        image = draw_friends_status(parent_avatar, parent_name, steam_status_data)
        uni_msg = UniMessage([Text("\n".join(msg)), Image(raw=image_to_bytes(image))])
    elif config.steam_broadcast_type == "part":
        images = [
            draw_start_gaming(
                (await fetch_avatar(entry["player"], avatar_path, config.proxy)),
                entry["player"]["personaname"],
                entry["player"]["gameextrainfo"],
                bind_data.get_by_steam_id(parent_id, entry["player"]["steamid"])[
                    "nickname"
                ],
            )
            for entry in play_data
            if entry["type"] == "start"
        ]
        if images == []:
            uni_msg = UniMessage([Text("\n".join(msg))])
        else:
            image = (
                vertically_concatenate_images(images) if len(images) > 1 else images[0]
            )
            uni_msg = UniMessage(
                [Text("\n".join(msg)), Image(raw=image_to_bytes(image))]
            )
    else:
        uni_msg = UniMessage([Text("\n".join(msg))])

    await uni_msg.send(
        Target(parent_id, parent_id, True, False, "", bot.adapter.get_name()), bot
    )


async def update_steam_info():
    steam_ids = bind_data.get_all_steam_id()

    steam_info = await get_steam_users_info(
        steam_ids, config.steam_api_key, config.proxy
    )

    old_players_dict: Dict[str, List[ProcessedPlayer]] = {}

    for parent_id in bind_data.content.keys():
        steam_ids = bind_data.get_all(parent_id)
        old_players_dict[parent_id] = steam_info_data.get_players(steam_ids)

    steam_info_data.update_by_players(steam_info["response"]["players"])
    steam_info_data.save()

    return bind_data, old_players_dict


@scheduler.scheduled_job(
    "interval", minutes=config.steam_request_interval / 60, id="update_steam_info"
)
async def fetch_and_broadcast_steam_info():
    bind_data, old_players_dict = await update_steam_info()

    for parent_id in bind_data.content.keys():
        old_players = old_players_dict[parent_id]
        new_players = steam_info_data.get_players(bind_data.get_all(parent_id))

        await broadcast_steam_info(parent_id, old_players, new_players)


if not config.steam_disable_broadcast_on_startup:
    nonebot.get_driver().on_bot_connect(update_steam_info)
else:
    logger.info("已禁用启动时的 Steam 播报")


@bind.handle()
async def bind_handle(
    event: Event, target: Target = Depends(get_target), cmd_arg: Message = CommandArg()
):
    parent_id = target.parent_id or target.id

    arg = cmd_arg.extract_plain_text()

    if not arg.isdigit():
        await bind.finish(
            "请输入正确的 Steam ID 或 Steam好友代码，格式: steambind [Steam ID 或 Steam好友代码]"
        )

    steam_id = get_steam_id(arg)

    if user_data := bind_data.get(parent_id, event.get_user_id()):
        user_data["steam_id"] = steam_id
        bind_data.save()

        await bind.finish(f"已更新你的 Steam ID 为 {steam_id}")
    else:
        bind_data.add(
            parent_id,
            {"user_id": event.get_user_id(), "steam_id": steam_id, "nickname": None},
        )
        bind_data.save()

        await bind.finish(f"已绑定你的 Steam ID 为 {steam_id}")


@unbind.handle()
async def unbind_handle(event: Event, target: Target = Depends(get_target)):
    parent_id = target.parent_id or target.id
    user_id = event.get_user_id()

    if bind_data.get(parent_id, user_id) is not None:
        bind_data.remove(parent_id, user_id)
        bind_data.save()

        await unbind.finish("已解绑 Steam ID")
    else:
        await unbind.finish("未绑定 Steam ID")


@info.handle()
async def info_handle(event: Event, target: Target = Depends(get_target)):
    parent_id = target.parent_id or target.id

    if user_data := bind_data.get(parent_id, event.get_user_id()):
        steam_id = user_data["steam_id"]
        steam_friend_code = str(int(steam_id) - STEAM_ID_OFFSET)

        await info.finish(
            f"你的 Steam ID: {steam_id}\n你的 Steam 好友代码: {steam_friend_code}"
        )
    else:
        await info.finish(
            "未绑定 Steam ID, 请使用 “steambind [Steam ID 或 Steam好友代码]” 绑定 Steam ID"
        )


@check.handle()
async def check_handle(
    target: Target = Depends(get_target), arg: Message = CommandArg()
):
    if arg.extract_plain_text().strip() != "":
        return None

    parent_id = target.parent_id or target.id

    steam_ids = bind_data.get_all(parent_id)

    steam_info = await get_steam_users_info(
        steam_ids, config.steam_api_key, config.proxy
    )

    logger.debug(f"{parent_id} Players info: {steam_info}")

    parent_avatar, parent_name = parent_data.get(parent_id)

    steam_status_data = [
        convert_player_name_to_nickname(
            (await simplize_steam_player_data(player, config.proxy, avatar_path)),
            parent_id,
            bind_data,
        )
        for player in steam_info["response"]["players"]
    ]

    image = draw_friends_status(parent_avatar, parent_name, steam_status_data)

    await target.send(UniMessage(Image(raw=image_to_bytes(image))))


@update_parent_info.handle()
async def update_parent_info_handle(
    bot: Bot,
    event: Event,
    target: Target = Depends(get_target),
    arg: Message = CommandArg(),
):
    msg = await UniMessage.generate(message=arg, event=event, bot=bot)
    info = {}
    for seg in msg:
        if isinstance(seg, Image):
            info["avatar"] = PILImage.open(BytesIO(await to_image_data(seg)))
        elif isinstance(seg, Text) and seg.text != "":
            info["name"] = seg.text

    if "avatar" not in info or "name" not in info:
        await update_parent_info.finish("文本中应包含图片和文字")

    parent_data.update(target.parent_id or target.id, info["avatar"], info["name"])
    await update_parent_info.finish("更新成功")


@enable.handle()
async def enable_handle(target: Target = Depends(get_target)):
    parent_id = target.parent_id or target.id

    disable_parent_data.remove(parent_id)
    disable_parent_data.save()

    await enable.finish("已启用 Steam 播报")


@disable.handle()
async def disable_handle(target: Target = Depends(get_target)):
    parent_id = target.parent_id or target.id

    disable_parent_data.add(parent_id)
    disable_parent_data.save()

    await disable.finish("已禁用 Steam 播报")


@set_nickname.handle()
async def set_nickname_handle(
    event: Event, target: Target = Depends(get_target), cmd_arg: Message = CommandArg()
):
    parent_id = target.parent_id or target.id

    nickname = cmd_arg.extract_plain_text().strip()

    if nickname == "":
        await set_nickname.finish("请输入昵称，格式: steamnickname [昵称]")

    user_data = bind_data.get(parent_id, event.get_user_id())

    if user_data is None:
        await set_nickname.finish(
            "未绑定 Steam ID，请先使用 steambind 绑定 Steam ID 后再设置昵称"
        )

    user_data["nickname"] = nickname
    bind_data.save()

    await set_nickname.finish(f"已设置你的昵称为 {nickname}，将在 Steam 播报中显示")

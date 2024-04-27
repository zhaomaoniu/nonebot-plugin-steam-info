import aiohttp
import nonebot
from io import BytesIO
from pathlib import Path
from nonebot.log import logger
from PIL import Image as PILImage
from typing import Union, Optional
from nonebot.params import Depends
from nonebot.params import CommandArg
from nonebot import on_command, require
from nonebot.adapters import Message, Event, Bot
from nonebot.plugin import PluginMetadata, inherit_supported_adapters

require("nonebot_plugin_alconna")
require("nonebot_plugin_localstore")
require("nonebot_plugin_apscheduler")

import nonebot_plugin_localstore as store
from nonebot_plugin_apscheduler import scheduler
from nonebot_plugin_alconna import Text, Image, UniMessage, Target

from .config import Config
from .models import PlayerSummaries
from .steam import get_steam_id, get_steam_users_info, STEAM_ID_OFFSET
from .data_source import BindData, SteamInfoData, ParentData, DisableParentData
from .draw import (
    check_font,
    image_to_bytes,
    draw_friends_status,
    simplize_steam_player_data,
)


__plugin_meta__ = PluginMetadata(
    name="Steam Info",
    description="播报绑定的 Steam 好友状态",
    usage="绑定 Steam ID: steambind [Steam ID 或 Steam好友代码]\n解绑 Steam ID: steamunbind\n查看 Steam ID: steaminfo\n查看 Steam 好友状态: steamcheck\n启用 Steam 播报: steamenable\n禁用 Steam 播报: steamdisable\n更新群信息: steamupdate",
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


async def broadcast_steam_info(parent_id: str, steam_info: PlayerSummaries):
    if disable_parent_data.is_disabled(parent_id):
        return None

    bot = nonebot.get_bot()

    msg = steam_info_data.compare(parent_id, steam_info["response"])

    if msg == []:
        return None

    steam_status_data = [
        await simplize_steam_player_data(player, config.proxy, avatar_path)
        for player in steam_info["response"]["players"]
    ]

    parent_avatar, parent_name = parent_data.get(parent_id)

    image = draw_friends_status(parent_avatar, parent_name, steam_status_data)

    await UniMessage([Text("\n".join(msg)), Image(raw=image_to_bytes(image))]).send(
        Target(parent_id, parent_id, True, False, "", bot.adapter.get_name()), bot
    )


@nonebot.get_driver().on_bot_connect
async def init_steam_info():
    for parent_id in bind_data.content:
        steam_ids = bind_data.get_all(parent_id)

        steam_info = await get_steam_users_info(
            steam_ids, config.steam_api_key, config.proxy
        )

        steam_info_data.update(parent_id, steam_info["response"])
        steam_info_data.save()


@scheduler.scheduled_job(
    "interval", minutes=config.steam_request_interval / 60, id="update_steam_info"
)
async def update_steam_info():
    for parent_id in bind_data.content:
        steam_ids = bind_data.get_all(parent_id)

        steam_info = await get_steam_users_info(
            steam_ids, config.steam_api_key, config.proxy
        )

        await broadcast_steam_info(parent_id, steam_info)

        steam_info_data.update(parent_id, steam_info["response"])
        steam_info_data.save()


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
        bind_data.add(parent_id, {"user_id": event.get_user_id(), "steam_id": steam_id})
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
        await simplize_steam_player_data(player, config.proxy, avatar_path)
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

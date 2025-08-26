import io
import re
import time
import httpx
import nonebot
from io import BytesIO
from pathlib import Path
from nonebot.log import logger
from PIL import Image as PILImage
from nonebot.params import Depends
from nonebot.params import CommandArg
from nonebot import on_command, on_notice, require
from typing import Union, Optional, List, Dict
from nonebot.adapters import Message, Event, Bot
from nonebot.adapters.onebot.v11 import MessageSegment, GroupMessageEvent, PrivateMessageEvent, GroupDecreaseNoticeEvent
from nonebot.adapters.onebot.v11.permission import GROUP_ADMIN, GROUP_OWNER
from nonebot.plugin import PluginMetadata, inherit_supported_adapters

require("nonebot_plugin_alconna")
require("nonebot_plugin_localstore")
require("nonebot_plugin_apscheduler")

import nonebot_plugin_localstore as store
from nonebot_plugin_apscheduler import scheduler
from nonebot_plugin_alconna import Text, Image, UniMessage, Target, At, MsgTarget

from .config import Config
from .models import ProcessedPlayer
from .data_source import BindData, SteamInfoData, ParentData, DisableParentData
from .steam import (
    get_steam_id,
    get_user_data,
    STEAM_ID_OFFSET,
    get_steam_users_info,
)
from .draw import (
    check_font,
    create_animated_steam_info,
    set_font_paths,
    draw_start_gaming,
    draw_player_status,
    draw_friends_status,
    vertically_concatenate_images,
)
from .utils import (
    fetch_avatar,
    image_to_bytes,
    simplize_steam_player_data,
    convert_player_name_to_nickname,
)

async def send_both(bot: Bot, event: Event, segments: MessageSegment) -> None:
    """
        自动判断message是 List 还是单个，发送{单个消息}，允许发送群和个人
    :param bot:
    :param event:
    :param segments:
    :return:
    """
    if isinstance(event, GroupMessageEvent):
        await bot.send_group_msg(group_id=event.group_id,
                                 message=Message(segments))
    elif isinstance(event, PrivateMessageEvent):
        await bot.send_private_msg(user_id=event.user_id,
                                   message=Message(segments))


__plugin_meta__ = PluginMetadata(
    name="Steam Info",
    description="播报绑定的 Steam 好友状态",
    usage="""
steamhelp: 查看帮助
steambind [Steam ID 或 Steam 好友代码]: 绑定 Steam ID
steamunbind: 解绑 Steam ID
steaminfo (可选)[@某人 或 Steam ID 或 Steam好友代码]: 查看 Steam 主页
steamcheck: 查看 Steam 好友状态
steamenable: 启用 Steam 播报
steamdisable: 禁用 Steam 播报
steamupdate [名称] [图片]: 更新群信息
steamnickname [昵称]: 设置玩家昵称
""".strip(),
    type="application",
    homepage="https://github.com/zhaomaoniu/nonebot-plugin-steam-info",
    config=Config,
    supported_adapters=inherit_supported_adapters("nonebot_plugin_alconna"),
)


help = on_command("steamhelp", aliases={"steam帮助"}, priority=10)
bind = on_command("steambind", aliases={"绑定steam"}, priority=10)
unbind = on_command("steamunbind", aliases={"解绑steam"}, priority=10)
info = on_command("steaminfo", aliases={"steam信息"}, priority=10)
check = on_command("steamcheck", aliases={"查看steam", "查steam"}, priority=10)
enable = on_command("steamenable", aliases={"启用steam"}, priority=10)
disable = on_command("steamdisable", aliases={"禁用steam"}, priority=10)
update_parent_info = on_command("steamupdate", aliases={"更新群信息"}, priority=10)
set_nickname = on_command("steamnickname", aliases={"steam昵称"}, priority=10)

group_decrease = on_notice(priority=10)


if hasattr(nonebot, "get_plugin_config"):
    config = nonebot.get_plugin_config(Config)
else:
    from nonebot import get_driver

    config = Config.parse_obj(get_driver().config)

set_font_paths(
    config.steam_font_regular_path,
    config.steam_font_light_path,
    config.steam_font_bold_path,
)

bind_data_path = store.get_data_file("nonebot_plugin_steam_info", "bind_data.json")
steam_info_data_path = store.get_data_file(
    "nonebot_plugin_steam_info", "steam_info.json"
)
parent_data_path = store.get_data_file("nonebot_plugin_steam_info", "parent_data.json")
disable_parent_data_path = store.get_data_file(
    "nonebot_plugin_steam_info", "disable_parent_data.json"
)
avatar_path = store.get_cache_dir("nonebot_plugin_steam_info")
cache_path = avatar_path

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


async def get_target(target: MsgTarget) -> Optional[Target]:
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
        async with httpx.AsyncClient() as client:
            response = await client.get(image.url)
            if response.status_code != 200:
                raise ValueError(f"无法获取图片数据: {response.status_code}")
            return response.content

    raise ValueError("无法获取图片数据")


async def broadcast_steam_info(
    parent_id: str,
    old_players: List[ProcessedPlayer],
    new_players: List[ProcessedPlayer],
):
    if disable_parent_data.is_disabled(parent_id):
        return None

    bot = nonebot.get_bot()
    blocked_appids = config.steam_blocked_appids
    
    filtered_new = []
    for player in new_players:
        if not player.get("gameextrainfo"):
            filtered_new.append(player)
            continue
        if player.get("gameid") not in blocked_appids:
            filtered_new.append(player)
            
    filtered_old = []
    for player in old_players:
        if not player.get("gameextrainfo"):
            filtered_old.append(player)
            continue
        if player.get("gameid") not in blocked_appids:
            filtered_old.append(player)

    play_data = steam_info_data.compare(filtered_old, filtered_new)

    msg = []
    for entry in play_data:
        player: ProcessedPlayer = entry["player"]
        old_player: ProcessedPlayer = entry.get("old_player")
        bind_info = bind_data.get_by_steam_id(parent_id, player["steamid"])
        qq_number = bind_info["user_id"] if bind_info else "未知"
        display_name = f"{player['personaname']}({qq_number})"

        if entry["type"] == "start":
            msg.append(f"{display_name} 开始玩 {player['gameextrainfo']} 了")
        elif entry["type"] == "stop":
            time_start = old_player["game_start_time"]
            time_stop = time.time()
            hours = int((time_stop - time_start) / 3600)
            minutes = int((time_stop - time_start) % 3600 / 60)
            time_str = (
                f"{hours} 小时 {minutes} 分钟" if hours > 0 else f"{minutes} 分钟"
            )
            msg.append(
                f"{display_name} 玩了 {time_str} {old_player['gameextrainfo']} 后不玩了"
            )
        elif entry["type"] == "change":
            msg.append(
                f"{display_name} 停止玩 {old_player['gameextrainfo']}，开始玩 {player['gameextrainfo']} 了"
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
    elif config.steam_broadcast_type == "none":
        uni_msg = UniMessage([Text("\n".join(msg))])
    else:
        logger.error(f"未知的播报类型: {config.steam_broadcast_type}")
        return None

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


@help.handle()
async def help_handle():
    await help.finish(__plugin_meta__.usage)


@bind.handle()
async def bind_handle(
    event: Event, target: Target = Depends(get_target), cmd_arg: Message = CommandArg(), permission=GROUP_ADMIN | GROUP_OWNER
):
    parent_id = target.parent_id or target.id
    target_user_id = event.get_user_id()

    arg = cmd_arg.extract_plain_text()
    
    at_list = (await UniMessage.generate(message=cmd_arg, event=event))[At]

    if at_list and permission:
        if len(at_list) > 1:
            await bind.finish("只能同时绑定一个用户")
        target_user_id = str(at_list[0].target)
        arg = re.search(r'\d+$', arg.strip()).group() if re.search(r'\d+$', arg.strip()) else ""
        
    print(arg)
    
    if not arg.isdigit():
        await bind.finish(
            "请输入正确的 Steam ID 或 Steam好友代码，格式: steambind [Steam ID 或 Steam好友代码]"
        )

    steam_id = get_steam_id(arg)
    if existing_user := bind_data.get_by_steam_id(parent_id, steam_id):
        await bind.finish(f"该Steam ID已被用户{existing_user['user_id']}绑定，请使用其他ID重新绑定")

    if user_data := bind_data.get(parent_id, target_user_id):
        user_data["steam_id"] = steam_id
        bind_data.save()

        await bind.finish(f"已更新你的 Steam ID 为 {steam_id}")
    else:
        bind_data.add(
            parent_id,
            {"user_id": target_user_id, "steam_id": steam_id, "nickname": None},
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
async def info_handle(
    bot: Bot,
    event: Event,
    target: Target = Depends(get_target),
    arg: Message = CommandArg(),
):
    parent_id = target.parent_id or target.id

    uni_arg = await UniMessage.generate(message=arg, event=event, bot=bot)
    at = uni_arg[At]

    if len(at) != 0:
        user_id: str = at[0].target
        user_data = bind_data.get(parent_id, user_id)
        if user_data is None:
            await info.finish("该用户未绑定 Steam ID")
        steam_id = user_data["steam_id"]
        steam_friend_code = str(int(steam_id) - STEAM_ID_OFFSET)
    elif arg.extract_plain_text().strip() != "":
        steam_id = int(arg.extract_plain_text().strip())
        if steam_id < STEAM_ID_OFFSET:
            steam_friend_code = steam_id
            steam_id += STEAM_ID_OFFSET
        else:
            steam_friend_code = steam_id - STEAM_ID_OFFSET
    else:
        user_data = bind_data.get(parent_id, event.get_user_id())

        if user_data is None:
            await info.finish(
                "未绑定 Steam ID, 请使用 “steambind [Steam ID 或 Steam好友代码]” 绑定 Steam ID"
            )

        steam_id = user_data["steam_id"]
        steam_friend_code = str(int(steam_id) - STEAM_ID_OFFSET)

    player_data = await get_user_data(steam_id, cache_path, config.proxy, config.steam_blocked_appids)
    
    draw_data = [
        {
            "game_header": game["game_image"],
            "game_name": game["game_name"],
            "game_time": f"{game['play_time']} 小时",
            "last_play_time": game["last_played"],
            "achievements": game["achievements"],
            "completed_achievement_number": game.get("completed_achievement_number"),
            "total_achievement_number": game.get("total_achievement_number"),
        }
        for game in player_data["game_data"]
    ]

    # 判断背景类型并生成对应图像
    avatar_image = PILImage.open(BytesIO(player_data["avatar"]))
    
    if player_data["background"]["type"] == "video":
        video_data = create_animated_steam_info(
            player_data["background"]["data"],
            avatar_image,
            player_data["avatar_gif"],
            player_data["player_name"],
            str(steam_friend_code),
            player_data["description"],
            player_data["recent_2_week_play_time"],
            draw_data
        )
        await send_both(bot, event, MessageSegment.video(video_data))
    else:
        # 生成静态图片
        background_img = PILImage.open(io.BytesIO(player_data["background"]["data"]))
        static_image = draw_player_status(
            background_img,
            player_data["avatar"],
            player_data["player_name"],
            str(steam_friend_code),
            player_data["description"],
            player_data["recent_2_week_play_time"],
            draw_data,
        )
        await info.finish(await UniMessage(Image(raw=image_to_bytes(static_image))).export(bot)
    )


@check.handle()
async def check_handle(
    bot: Bot, target: Target = Depends(get_target), arg: Message = CommandArg()
):
    if arg.extract_plain_text().strip() != "":
        return None

    parent_id = target.parent_id or target.id
    try:
        member_list = await bot.get_group_member_list(group_id=parent_id)
        current_member_uids = [str(member["user_id"]) for member in member_list]
    except Exception as e:
        await check.finish(f"获取群成员列表失败: {str(e)}")
    
    # 清理逻辑
    removed_count = 0
    group_bindings = bind_data.content.get(str(parent_id), [])
    for binding in group_bindings.copy():
        user_id = binding["user_id"]
        if user_id not in current_member_uids:
            bind_data.remove(str(parent_id), user_id)
            removed_count += 1
    
    if removed_count > 0:
        bind_data.save()
        await check.send(f"已清理{removed_count}个已离群用户的绑定信息")

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

@group_decrease.handle()
async def handle_group_decrease(event: GroupDecreaseNoticeEvent):
    """处理用户退群事件，删除其在该群的绑定数据"""
    if event.is_tome():
        return
    
    user_id = event.user_id
    group_id = event.group_id
    
    if bind_data.get(str(group_id), str(user_id)):
        bind_data.remove(str(group_id), str(user_id))
        bind_data.save()
        logger.info(f"用户 {user_id} 退出群 {group_id}，已删除其Steam绑定数据")

# 定时关闭播报任务
async def schedule_close_broadcast():
    """定时关闭所有群组的播报功能"""
    for parent_id in bind_data.content.keys():
        if not disable_parent_data.is_disabled(parent_id):
            disable_parent_data.add(parent_id)
    disable_parent_data.save()

# 定时开启播报任务
async def schedule_open_broadcast():
    """定时开启所有群组的播报功能"""
    for parent_id in bind_data.content.keys():
        if disable_parent_data.is_disabled(parent_id):
            disable_parent_data.remove(parent_id)
    disable_parent_data.save()

def setup_schedule_tasks():
    if config.steam_schedule_enabled != 1:
        return

    close_hour, close_minute = map(int, config.steam_schedule_close_time.split(":"))
    open_hour, open_minute = map(int, config.steam_schedule_open_time.split(":"))
    
    scheduler.add_job(
        schedule_close_broadcast,
        "cron",
        hour=close_hour,
        minute=close_minute,
        id="steam_schedule_close",
        replace_existing=True
    )
    logger.info(f"已设置定时关闭播报: 每天 {config.steam_schedule_close_time}")

    scheduler.add_job(
        schedule_open_broadcast,
        "cron",
        hour=open_hour,
        minute=open_minute,
        id="steam_schedule_open",
        replace_existing=True
    )
    logger.info(f"已设置定时开启播报: 每天 {config.steam_schedule_open_time}")

# 在插件加载时设置定时任务
setup_schedule_tasks()
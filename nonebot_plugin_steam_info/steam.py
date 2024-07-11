import aiohttp
from typing import List
from nonebot.log import logger

from .models import PlayerSummaries


STEAM_ID_OFFSET = 76561197960265728


def get_steam_id(steam_id_or_steam_friends_code: str) -> str:
    if not steam_id_or_steam_friends_code.isdigit():
        return None

    id_ = int(steam_id_or_steam_friends_code)

    if id_ < STEAM_ID_OFFSET:
        return str(id_ + STEAM_ID_OFFSET)

    return steam_id_or_steam_friends_code


async def get_steam_users_info(
    steam_ids: List[str], steam_api_key: List[str], proxy: str = None
) -> PlayerSummaries:
    if len(steam_ids) == 0:
        return {"response": {"players": []}}

    if len(steam_ids) > 100:
        # 分批获取
        result = {"response": {"players": []}}
        for i in range(0, len(steam_ids), 100):
            result["response"]["players"].extend(
                (
                    await get_steam_users_info(
                        steam_ids[i : i + 100], steam_api_key, proxy
                    )
                )["response"]["players"]
            )
        return result

    for api_key in steam_api_key:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f'http://api.steampowered.com/ISteamUser/GetPlayerSummaries/v0002/?key={api_key}&steamids={",".join(steam_ids)}',
                proxy=proxy,
            ) as resp:
                if resp.status == 200:
                    return await resp.json()
                else:
                    logger.warning(f"API key {api_key} failed to get steam users info.")

    logger.error("All API keys failed to get steam users info.")
    return {"response": {"players": []}}

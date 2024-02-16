import aiohttp
from typing import List

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
    steam_ids: List[str], steam_api_key: str, proxy: str = None
) -> PlayerSummaries:
    if len(steam_ids) == 0:
        return {"response": {"players": []}}

    elif len(steam_ids) > 100:
        # TODO: 分批请求
        raise ValueError("The maximum number of steam ids is 100")

    async with aiohttp.ClientSession() as session:
        async with session.get(
            f'http://api.steampowered.com/ISteamUser/GetPlayerSummaries/v0002/?key={steam_api_key}&steamids={",".join(steam_ids)}',
            proxy=proxy,
        ) as resp:
            if resp.status != 200:
                raise ValueError(
                    f"Failed to get steam users info: {resp.status}, {await resp.text()}"
                )
            return await resp.json()

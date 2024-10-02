import re
import json
import httpx
from pathlib import Path
from nonebot.log import logger
from typing import List, Optional, Dict

from .models import PlayerSummaries, OwnedGames, AppDetails


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
            batch_result = await get_steam_users_info(
                steam_ids[i : i + 100], steam_api_key, proxy
            )
            result["response"]["players"].extend(batch_result["response"]["players"])
        return result

    for api_key in steam_api_key:
        try:
            async with httpx.AsyncClient(proxy=proxy) as client:
                response = await client.get(
                    f'http://api.steampowered.com/ISteamUser/GetPlayerSummaries/v0002/?key={api_key}&steamids={",".join(steam_ids)}'
                )
                if response.status_code == 200:
                    return response.json()
                else:
                    logger.warning(f"API key {api_key} failed to get steam users info.")
        except httpx.RequestError as exc:
            logger.warning(f"API key {api_key} encountered an error: {exc}")

    logger.error("All API keys failed to get steam users info.")
    return {"response": {"players": []}}


async def get_owned_games(
    steam_id: str, steam_api_key: List[str], proxy: str = None
) -> OwnedGames:
    for api_key in steam_api_key:
        try:
            async with httpx.AsyncClient(proxy=proxy) as client:
                response = await client.get(
                    f"http://api.steampowered.com/IPlayerService/GetOwnedGames/v0001/?key={api_key}&steamid={steam_id}&include_appinfo=true"
                )
                if response.status_code == 200:
                    return response.json()
                else:
                    logger.warning(f"API key {api_key} failed to get owned games.")
        except httpx.RequestError as exc:
            logger.warning(f"API key {api_key} encountered an error: {exc}")

    logger.error("All API keys failed to get owned games.")


async def get_game_header(
    appid: int, cache_path: Path, proxy: str = None
) -> Optional[bytes]:
    # check cache
    if (cache_path / f"{appid}_header.jpg").exists():
        return (cache_path / f"{appid}_header.jpg").read_bytes()

    result = None
    try:
        async with httpx.AsyncClient(proxy=proxy) as client:
            response = await client.get(
                f"https://shared.steamstatic.com/store_item_assets/steam/apps/{appid}/header_schinese.jpg"
            )
            if response.status_code == 200:
                result = response.content
            else:
                response = await client.get(
                    f"https://shared.steamstatic.com/store_item_assets/steam/apps/{appid}/header.jpg"
                )
                if response.status_code == 200:
                    result = response.content
                else:
                    response.raise_for_status()
        # cache the image
        (cache_path / f"{appid}_header.jpg").write_bytes(result)
        return result

    except httpx.RequestError as exc:
        logger.error(f"Failed to get game header: {exc}")
        return None


async def get_game_icon(
    appid: int, hash: str, cache_path: Path, proxy: str = None
) -> Optional[bytes]:
    # check cache
    if (cache_path / f"{appid}_{hash}_icon.jpg").exists():
        return (cache_path / f"{appid}_{hash}_icon.jpg").read_bytes()

    result = None
    try:
        async with httpx.AsyncClient(proxy=proxy) as client:
            response = await client.get(
                f"https://media.steampowered.com/steamcommunity/public/images/apps/{appid}/{hash}.jpg"
            )
            if response.status_code == 200:
                result = response.content
            else:
                response.raise_for_status()
        # cache the image
        (cache_path / f"{appid}_{hash}_icon.jpg").write_bytes(result)
        return result

    except httpx.RequestError as exc:
        logger.error(f"Failed to get game icon: {exc}")
        return None


async def get_games_details(
    appids: List[int], cache_path: Path, proxy: str = None
) -> Optional[Dict[int, AppDetails]]:
    result = {}

    for appid in appids:
        cache_file = cache_path / f"{appid}_appdetails.json"

        # check cache
        if cache_file.exists():
            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    result[appid] = json.load(f)
                    continue
            except json.JSONDecodeError:
                logger.warning(f"Failed to read cache file {cache_file}")

        try:
            async with httpx.AsyncClient(
                proxy=proxy,
                headers={
                    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6"
                },
            ) as client:
                response = await client.get(
                    f"https://store.steampowered.com/api/appdetails?appids={appid}"
                )
                if response.status_code == 200:
                    try:
                        appdetails = response.json()[str(appid)]
                    except json.JSONDecodeError:
                        logger.warning(
                            f"Failed to parse game details for appid {appid}"
                        )
                        continue
                    if not appdetails["success"]:
                        logger.warning(f"Failed to get game details for appid {appid}")
                        continue
                    result[appid] = appdetails
                    # cache the result
                    with open(cache_file, "w", encoding="utf-8") as f:
                        json.dump(appdetails, f, ensure_ascii=False)
                else:
                    response.raise_for_status()
        except httpx.RequestError as exc:
            logger.error(f"Failed to get game details for appid {appid}: {exc}")
            return None

    return result


async def get_user_data(steam_id: int, proxy: str = None) -> Dict:
    url = f"https://steamcommunity.com/profiles/{steam_id}"
    default_background = (Path(__file__).parent / "res/bg_dots.png").read_bytes()

    try:
        async with httpx.AsyncClient(proxy=proxy) as client:
            response = await client.get(url)
            if response.status_code == 200:
                html = response.text
            else:
                response.raise_for_status()
    except httpx.RequestError as exc:
        logger.error(f"Failed to get user data: {exc}")
        return {}

    # description <meta property="twitter:description" content="这是一条概要ːmurasame_smileː">
    description = re.search(
        r'<meta property="twitter:description" content="(.*?)">', html
    )
    if description:
        description = description.group(1)
    else:
        description = "No imformation given."
    
    # remove emoji
    description = re.sub(r"ː.*?ː", "", description)

    # background
    background_url = re.search(r"background-image: url\( \'(.*?)\' \)", html)
    if background_url:
        background_url = background_url.group(1)
    else:
        background_url = None

    try:
        async with httpx.AsyncClient(proxy=proxy) as client:
            response = await client.get(background_url)
            if response.status_code == 200:
                background = response.content
            else:
                response.raise_for_status()
    except httpx.RequestError as exc:
        logger.error(f"Failed to get user background: {exc}")
        return {"description": description, "background": default_background}

    return {"description": description, "background": background}


if __name__ == "__main__":
    from nonebot.log import logger
    import asyncio

    data = asyncio.run(get_user_data(76561199135038179, None))

    with open("bg.jpg", "wb") as f:
        f.write(data["background"])
    logger.info(data["description"])

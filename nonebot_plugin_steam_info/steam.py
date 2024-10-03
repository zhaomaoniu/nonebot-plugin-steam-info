import re
import httpx
from pathlib import Path
from bs4 import BeautifulSoup
from nonebot.log import logger
from typing import List, Optional, Dict

from .models import PlayerSummaries, PlayerData


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


async def _fetch(
    url: str, default: bytes, cache_file: Optional[Path] = None, proxy: str = None
) -> bytes:
    if cache_file is not None and cache_file.exists():
        return cache_file.read_bytes()
    try:
        async with httpx.AsyncClient(proxy=proxy) as client:
            response = await client.get(url)
            if response.status_code == 200:
                if cache_file is not None:
                    cache_file.write_bytes(response.content)
                return response.content
            else:
                response.raise_for_status()
    except Exception as exc:
        logger.error(f"Failed to get image: {exc}")
        return default


async def get_user_data(
    steam_id: int, cache_path: Path, proxy: str = None
) -> PlayerData:
    url = f"https://steamcommunity.com/profiles/{steam_id}"
    default_background = (Path(__file__).parent / "res/bg_dots.png").read_bytes()
    default_avatar = (Path(__file__).parent / "res/unknown_avatar.jpg").read_bytes()
    default_achievement_image = (
        Path(__file__).parent / "res/default_achievement_image.png"
    ).read_bytes()
    default_header_image = (
        Path(__file__).parent / "res/default_header_image.jpg"
    ).read_bytes()

    result = {
        "description": "No imformation given.",
        "background": default_background,
        "avatar": default_avatar,
        "player_name": "Unknown",
        "recent_2_week_play_time": None,
        "game_data": [],
    }

    try:
        async with httpx.AsyncClient(
            proxy=proxy,
            headers={
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6"
            },
        ) as client:
            response = await client.get(url)
            if response.status_code == 200:
                html = response.text
            elif response.status_code == 302:
                url = response.headers["Location"]
                response = await client.get(url)
                if response.status_code == 200:
                    html = response.text
            else:
                response.raise_for_status()
    except httpx.RequestError as exc:
        logger.error(f"Failed to get user data: {exc}")
        return result

    # player name
    player_name = re.search(r"<title>Steam 社区 :: (.*?)</title>", html)
    if player_name:
        result["player_name"] = player_name.group(1)

    # description t<div class="profile_summary">\r\n\t\t\t\t\t\t\t\t風が雨が激しくても<br>思いだすんだ 僕らを照らす光があるよ<br>今日もいっぱい<br>明日もいっぱい 力を出しきってみるよ\t\t\t\t\t\t\t</div>
    description = re.search(
        r'<div class="profile_summary">(.*?)</div>', html, re.DOTALL | re.MULTILINE
    )
    if description:
        description = description.group(1)
        description = re.sub(r"<br>", "\n", description)
        description = re.sub(r"\t", "", description)
        result["description"] = description.strip()

    # remove emoji
    result["description"] = re.sub(r"ː.*?ː", "", result["description"])

    # remove xml
    result["description"] = re.sub(r"<.*?>", "", result["description"])

    # background
    background_url = re.search(r"background-image: url\( \'(.*?)\' \)", html)
    if background_url:
        background_url = background_url.group(1)
        result["background"] = await _fetch(
            background_url, default_background, proxy=proxy
        )

    # avatar
    # \t<link rel="image_src" href="https://avatars.akamai.steamstatic.com/3ade30f61c3d2cc0b8c80aaf567b573cd022c405_full.jpg">
    avatar_url = re.search(r'<link rel="image_src" href="(.*?)"', html)
    if avatar_url:
        avatar_url = avatar_url.group(1)
        # https://avatars.akamai.steamstatic.com/3ade30f61c3d2cc0b8c80aaf567b573cd022c405_full.jpg
        avatar_url_split = avatar_url.split("/")
        avatar_file = cache_path / f"avatar_{avatar_url_split[-1].split('_')[0]}.jpg"
        result["avatar"] = await _fetch(
            avatar_url, default_avatar, cache_file=avatar_file, proxy=proxy
        )

    # recent 2 week play time
    # \t<div class="recentgame_quicklinks recentgame_recentplaytime">\r\n\t\t\t\t\t\t\t\t\t<div>15.5 小时（过去 2 周）</div>
    play_time_text = re.search(
        r'<div class="recentgame_quicklinks recentgame_recentplaytime">\s*<div>(.*?)</div>',
        html,
    )
    if play_time_text:
        play_time_text = play_time_text.group(1)
        result["recent_2_week_play_time"] = play_time_text

    # game data
    soup = BeautifulSoup(html, "html.parser")
    game_data = []
    recent_games = soup.find_all("div", class_="recent_game")

    for game in recent_games:
        game_info = {}
        game_info["game_name"] = game.find("div", class_="game_name").text.strip()
        game_info["game_image_url"] = game.find("img", class_="game_capsule")["src"]
        game_info_split = game_info["game_image_url"].split("/")
        # https://shared.akamai.steamstatic.com/store_item_assets/steam/apps/1144400/capsule_184x69_schinese.jpg?t=1724440433

        game_info["game_image"] = await _fetch(
            game_info["game_image_url"],
            default_header_image,
            cache_file=cache_path / f"header_{game_info_split[-2]}.jpg",
            proxy=proxy,
        )

        play_time_text = game.find("div", class_="game_info_details").text.strip()
        game_info["play_time"] = re.search(
            r"总时数\s*(.*?)\s*小时", play_time_text
        ).group(1)
        game_info["last_played"] = (
            re.search(r"最后运行日期：(.*) 日", play_time_text).group(1).strip() + " 日"
        )
        achievements = []
        achievement_elements = game.find_all("div", class_="game_info_achievement")
        for achievement in achievement_elements:
            if "plus_more" in achievement["class"]:
                continue
            achievement_info = {}
            achievement_info["name"] = achievement["data-tooltip-text"]
            achievement_info["image_url"] = achievement.find("img")["src"]
            achievement_info_split = achievement_info["image_url"].split("/")

            achievement_info["image"] = await _fetch(
                achievement_info["image_url"],
                default_achievement_image,
                cache_file=cache_path
                / f"achievement_{achievement_info_split[-2]}_{achievement_info_split[-1]}",
                proxy=proxy,
            )
            achievements.append(achievement_info)
        game_info["achievements"] = achievements
        game_info_achievement_summary = game.find(
            "span", class_="game_info_achievement_summary"
        )
        if game_info_achievement_summary is None:
            game_data.append(game_info)
            continue
        remain_achievement_text = game_info_achievement_summary.find(
            "span", class_="ellipsis"
        ).text
        game_info["completed_achievement_number"] = int(
            remain_achievement_text.split("/")[0].strip()
        )
        game_info["total_achievement_number"] = int(
            remain_achievement_text.split("/")[1].strip()
        )

        game_data.append(game_info)

    result["game_data"] = game_data

    return result


if __name__ == "__main__":
    from nonebot.log import logger
    import asyncio

    data = asyncio.run(get_user_data(76561199135038179, None))

    with open("bg.jpg", "wb") as f:
        f.write(data["background"])
    logger.info(data["description"])

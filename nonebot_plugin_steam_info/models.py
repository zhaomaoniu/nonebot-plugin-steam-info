from typing import TypedDict, List, Dict, Optional


class Player(TypedDict):
    steamid: str
    communityvisibilitystate: int
    profilestate: int
    personaname: str
    profileurl: str
    avatar: str
    avatarmedium: str
    avatarfull: str
    avatarhash: str
    lastlogoff: int
    personastate: int
    realname: str
    primaryclanid: str
    timecreated: int
    personastateflags: int
    # gameextrainfo: str
    # gameid: str


class PlayerSummariesResponse(TypedDict):
    players: List[Player]


class PlayerSummaries(TypedDict):
    response: PlayerSummariesResponse


class ProcessedPlayer(TypedDict):
    steamid: str
    communityvisibilitystate: int
    personaname: str
    profileurl: str
    avatar: str
    avatarmedium: str
    avatarfull: str
    avatarhash: str
    lastlogoff: int
    personastate: int
    realname: str
    primaryclanid: str
    timecreated: int
    personastateflags: int

    game_start_time: int  # Unix timestamp


class PlayerSummariesProcessedResponse(TypedDict):
    players: List[ProcessedPlayer]


class Game(TypedDict):
    appid: int
    name: str
    playtime_forever: int
    img_icon_url: str
    rtime_last_played: int
    playtime_disconnected: int


class OwnedGamesResponse(TypedDict):
    game_count: int
    games: List[Game]


class OwnedGames(TypedDict):
    response: OwnedGamesResponse


class PriceOverview(TypedDict, total=False):
    currency: str
    initial: int
    final: int
    discount_percent: int
    initial_formatted: str
    final_formatted: str


class PackageGroup(TypedDict, total=False):
    name: str
    title: str
    description: str
    selection_text: str
    display_type: int
    is_recurring_subscription: str
    subs: List[Dict]


class Category(TypedDict, total=False):
    id: int
    description: str


class Genre(TypedDict, total=False):
    id: str
    description: str


class Screenshot(TypedDict, total=False):
    id: int
    path_thumbnail: str
    path_full: str


class Movie(TypedDict, total=False):
    id: int
    name: str
    thumbnail: str
    webm: Dict[str, str]
    mp4: Dict[str, str]
    highlight: bool


class Achievement(TypedDict, total=False):
    name: str
    path: str


class GameData(TypedDict, total=False):
    type: str
    name: str
    steam_appid: int
    required_age: int
    is_free: bool
    detailed_description: str
    about_the_game: str
    short_description: str
    supported_languages: str
    header_image: str
    capsule_image: str
    capsule_imagev5: str
    website: str
    price_overview: PriceOverview
    packages: List[int]
    package_groups: List[PackageGroup]
    platforms: Dict[str, bool]
    categories: List[Category]
    genres: List[Genre]
    screenshots: List[Screenshot]
    movies: List[Movie]
    achievements: Dict[str, List[Achievement]]
    release_date: Dict[str, Optional[str]]
    support_info: Dict[str, Optional[str]]
    background: str
    background_raw: str
    content_descriptors: Dict[str, Optional[List[int]]]


class AppDetails(TypedDict, total=False):
    success: bool
    data: GameData


class DrawPlayerStatusData(TypedDict):
    game_name: str
    game_time: str # e.g. 10.2 小时
    last_play_time: str # e.g. 10 月 2 日
    game_header: bytes


__all__ = [
    "Player",
    "PlayerSummaries",
    "PlayerSummariesResponse",
    "ProcessedPlayer",
    "PlayerSummariesProcessedResponse",
    "OwnedGames",
    "AppDetails",
]

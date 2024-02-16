from typing import TypedDict, List


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

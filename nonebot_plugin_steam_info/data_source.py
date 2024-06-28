import json
import time
from PIL import Image
from pathlib import Path
from typing import Any, List, Dict, Optional, Tuple

from .models import Player, ProcessedPlayer


class BindData:
    def __init__(self, save_path: Path) -> None:
        self.content: Dict[str, List[Dict[str, str]]] = {}
        self._save_path = save_path

        if save_path.exists():
            self.content = json.loads(Path(save_path).read_text("utf-8"))
        else:
            self.save()

    def save(self) -> None:
        with open(self._save_path, "w", encoding="utf-8") as f:
            json.dump(self.content, f, indent=4)

    def add(self, parent_id: str, content: Dict[str, str]) -> None:
        if parent_id not in self.content:
            self.content[parent_id] = [content]
        else:
            self.content[parent_id].append(content)

    def remove(self, parent_id: str, user_id: str) -> None:
        if parent_id not in self.content:
            return
        for data in self.content[parent_id]:
            if data["user_id"] == user_id:
                self.content[parent_id].remove(data)
                break

    def update(self, parent_id: str, content: Dict[str, str]) -> None:
        self.content[parent_id] = content

    def get(self, parent_id: str, user_id: str) -> Optional[Dict[str, str]]:
        if parent_id not in self.content:
            return None
        for data in self.content[parent_id]:
            if data["user_id"] == user_id:
                if not data.get("nickname"):
                    data["nickname"] = None
                return data
        return None

    def get_by_steam_id(
        self, parent_id: str, steam_id: str
    ) -> Optional[Dict[str, str]]:
        if parent_id not in self.content:
            return None
        for data in self.content[parent_id]:
            if data["steam_id"] == steam_id:
                if not data.get("nickname"):
                    data["nickname"] = None
                return data
        return None

    def get_all(self, parent_id: str) -> List[str]:
        if parent_id not in self.content:
            return []

        result = []

        for data in self.content[parent_id]:
            if not data["steam_id"] in result:
                result.append(data["steam_id"])

        return result

    def get_all_steam_id(self) -> List[str]:
        result = []
        for parent_id in self.content:
            for data in self.content[parent_id]:
                if not data["steam_id"] in result:
                    result.append(data["steam_id"])
        return result


class SteamInfoData:
    def __init__(self, save_path: Path) -> None:
        self.content: List[ProcessedPlayer] = []
        self._save_path = save_path

        if save_path.exists():
            self.content = json.loads(save_path.read_text("utf-8"))
            if isinstance(self.content, dict):
                self.content = []
                self.save()
        else:
            self.save()

    def save(self) -> None:
        with open(self._save_path, "w", encoding="utf-8") as f:
            json.dump(self.content, f, indent=4)

    def update(self, player: ProcessedPlayer) -> None:
        self.content.append(player)

    def update_by_players(self, players: List[Player]):
        # 将 Player 转换为 ProcessedPlayer
        processed_players = []
        for player in players:
            old_player = self.get_player(player["steamid"])

            if old_player is None:
                if player.get("gameextrainfo") is not None:
                    player["game_start_time"] = int(time.time())
                else:
                    player["game_start_time"] = None
                processed_players.append(player)
            else:
                if (
                    player.get("gameextrainfo") is not None
                    and old_player.get("gameextrainfo") is None
                ):
                    # 开始游戏
                    player["game_start_time"] = int(time.time())
                elif (
                    player.get("gameextrainfo") is None
                    and old_player.get("gameextrainfo") is not None
                ):
                    # 结束游戏
                    player["game_start_time"] = None
                elif (
                    player.get("gameextrainfo") is not None
                    and old_player.get("gameextrainfo") is not None
                ):
                    # 继续游戏
                    player["game_start_time"] = old_player["game_start_time"]
                else:
                    player["game_start_time"] = None
                processed_players.append(player)

        self.content = processed_players

    def get_player(self, steam_id: str) -> Optional[Player]:
        for player in self.content:
            if player["steamid"] == steam_id:
                return player
        return None

    def get_players(self, steam_ids: List[str]) -> List[Player]:
        result = []
        for player in self.content:
            if player["steamid"] in steam_ids:
                result.append(player)
        return result

    def compare(
        self, old_players: List[Player], new_players: List[Player]
    ) -> List[Dict[str, Any]]:
        result = []

        for player in new_players:
            for old_player in old_players:
                if player["steamid"] == old_player["steamid"]:
                    if player.get("gameextrainfo") != old_player.get("gameextrainfo"):
                        if player.get("gameextrainfo") is not None:
                            result.append(
                                {
                                    "type": "start",
                                    "player": player,
                                    "old_player": old_player,
                                }
                            )
                        elif old_player.get("gameextrainfo") is not None:
                            result.append(
                                {
                                    "type": "stop",
                                    "player": player,
                                    "old_player": old_player,
                                }
                            )
                        elif (
                            player.get("gameextrainfo") is not None
                            and old_player.get("gameextrainfo") is not None
                        ):
                            result.append(
                                {
                                    "type": "change",
                                    "player": player,
                                    "old_player": old_player,
                                }
                            )
                        else:
                            result.append(
                                {
                                    "type": "error",
                                    "player": player,
                                    "old_player": old_player,
                                }
                            )
        return result


class ParentData:
    def __init__(self, save_path: Path) -> None:
        self.content: Dict[str, str] = {}  # parent_id: name
        self._save_path = save_path

        if not save_path.exists():
            save_path.parent.mkdir(parents=True, exist_ok=True)
            self.save()
        else:
            self.content = json.loads(save_path.read_text("utf-8"))

    def save(self) -> None:
        with open(self._save_path, "w", encoding="utf-8") as f:
            json.dump(self.content, f, indent=4)

    def update(self, parent_id: str, avatar: Image.Image, name: str) -> None:
        self.content[parent_id] = name
        self.save()
        # 保存图片
        avatar_path = self._save_path.parent / f"{parent_id}.png"
        avatar.save(avatar_path)

    def get(self, parent_id: str) -> Tuple[Image.Image, str]:
        if parent_id not in self.content:
            return (
                Image.open(Path(__file__).parent / "res/unknown_avatar.jpg"),
                parent_id,
            )
        avatar_path = self._save_path.parent / f"{parent_id}.png"
        return Image.open(avatar_path), self.content[parent_id]


class DisableParentData:
    """储存禁用 Steam 通知的 parent"""

    def __init__(self, save_path: Path) -> None:
        self.content: List[str] = []
        self._save_path = save_path

        if save_path.exists():
            self.content = json.loads(save_path.read_text("utf-8"))
        else:
            self.save()

    def save(self) -> None:
        with open(self._save_path, "w", encoding="utf-8") as f:
            json.dump(self.content, f, indent=4)

    def add(self, parent_id: str) -> None:
        if parent_id not in self.content:
            self.content.append(parent_id)
            self.save()

    def remove(self, parent_id: str) -> None:
        if parent_id in self.content:
            self.content.remove(parent_id)
            self.save()

    def is_disabled(self, parent_id: str) -> bool:
        return parent_id in self.content

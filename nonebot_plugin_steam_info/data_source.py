import json
from PIL import Image
from pathlib import Path
from typing import List, Dict, Optional, Tuple

from .models import PlayerSummariesResponse


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


class SteamInfoData:
    def __init__(self, save_path: Path) -> None:
        self.content: Dict[str, PlayerSummariesResponse] = {}
        self._save_path = save_path

        if save_path.exists():
            self.content = json.loads(save_path.read_text("utf-8"))
        else:
            self.save()

    def save(self) -> None:
        with open(self._save_path, "w", encoding="utf-8") as f:
            json.dump(self.content, f, indent=4)

    def update(self, parent_id: str, content: PlayerSummariesResponse) -> None:
        self.content[parent_id] = content

    def get(self, parent_id: str) -> Optional[PlayerSummariesResponse]:
        return self.content.get(parent_id, None)

    def compare(
        self, parent_id: str, new_content: PlayerSummariesResponse
    ) -> List[str]:
        old_content = self.get(parent_id)

        if old_content is None:
            self.update(parent_id, new_content)
            self.save()
            return []

        result = []

        for player in new_content["players"]:
            for old_player in old_content["players"]:
                if player["steamid"] == old_player["steamid"]:
                    if player.get("gameextrainfo") != old_player.get("gameextrainfo"):
                        if player.get("gameextrainfo") is not None:
                            result.append(
                                f"{player['personaname']} 开始玩 {player['gameextrainfo']} 了"
                            )
                        elif old_player.get("gameextrainfo") is not None:
                            result.append(
                                f"{player['personaname']} 停止玩 {old_player['gameextrainfo']} 了"
                            )
                        elif (
                            player.get("gameextrainfo") is not None
                            and old_player.get("gameextrainfo") is not None
                        ):
                            result.append(
                                f"{player['personaname']} 停止玩 {old_player['gameextrainfo']}，开始玩 {player['gameextrainfo']} 了"
                            )
                        else:
                            result.append(
                                f"出现错误！{player['personaname']}\nNew: {player.get('gameextrainfo')}\nOld: {old_player.get('gameextrainfo')}"
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

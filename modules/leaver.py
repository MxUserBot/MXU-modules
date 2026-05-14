#			__  ____  ___   _               _           _   
#			|  \/  \ \/ / | | |___  ___ _ __| |__   ___ | |_ 
#			| |\/| |\  /| | | / __|/ _ \ '__| '_ \ / _ \| __|
#			| |  | |/  \| |_| \__ \  __/ |  | |_) | (_) | |_ 
#			|_|  |_/_/\_\\___/|___/\___|_|  |_.__/ \___/ \__| 
#
# 🔒      Licensed under the GNU AGPLv3
# 🌐 https://www.gnu.org/licenses/agpl-3.0.html


class Meta:
    name = "ChatMassacre"
    description = "leaver chats"
    version = "3.2.0"
    tags = ["utility", "admin"]
    author = "https://github.com/PashaHatsune"


import asyncio
from typing import Any

from mautrix.types import EventType
from pydantic import BaseModel, model_validator

from mxc import utils
from mxc.exceptions import UsageError
from .. import loader


class LeavePayload(BaseModel):
    mode: str = None
    target: str = ""

    @model_validator(mode="before")
    @classmethod
    def parse(cls, v: Any):
        if isinstance(v, str):
            parts = v.split(maxsplit=1)
            if not parts:
                return {"mode": "all", "target": ""}
            first = parts[0].lower()
            if first == "--all":
                return {"mode": "all", "target": ""}
            if first in ("u", "n", "id"):
                return {
                    "mode": first,
                    "target": parts[1] if len(parts) > 1 else "",
                }
            raise UsageError("Invalid mode. Use u, n, id, or --all")
        return {"mode": "all", "target": ""} if not v else v


@loader.tds
class ChatMassacreModule(loader.Module):
    strings = {
        "starting": "🚀 <b>Initiating cleansing protocol...</b><br>Mode: <code>{mode}</code> | Target: <code>{target}</code>",
        "finished": "✅ <b>Cleansing complete.</b><br>Left <b>{count}</b> rooms.",
    }


    def __init__(self):
        self.checkers = {
            "u": self._check_user,
            "n": self._check_name,
            "id": self._check_id
        }


    async def _check_user(
        self,
        mx,
        room_id: str,
        target: str
    ) -> bool:
        members = await mx.client.get_joined_members(room_id)
        return target in members


    async def _check_name(
        self,
        mx,
        room_id: str,
        target: str
    ) -> bool:
        try:
            name_evt = await mx.client.get_state_event(room_id, EventType.ROOM_NAME)
            room_name = name_evt.get("name", "") if name_evt else ""
            return target.lower() in room_name.lower()
        except Exception:
            return False


    async def _check_id(
        self,
        mx,
        room_id: str,
        target: str
    ) -> bool:
        target_ids =[r.strip() for r in target.split(",")]
        return room_id in target_ids


    @loader.command(name="leave")
    async def leave_cmd(
        self,
        mx,
        event,
        payload: LeavePayload = LeavePayload()
    ):
        """[--all | <u/n/id> <target>] - Mass leave rooms by User, Name, IDs, or all"""

        if payload.mode == "all":
            g = await utils.answer(
                mx,
                "🚀 <b>Initiating cleansing protocol...</b><br>Mode: <code>all</code>"
            )
            log_room = await self._get("log_room_id")
            joined_rooms = await mx.client.get_joined_rooms()
            count = 0

            for room_id in joined_rooms:
                if room_id == event.room_id:
                    continue
                try:
                    self.logger.warning(f"Leaving room {room_id}")
                    await mx.client.leave_room(room_id)
                    count += 1
                    await asyncio.sleep(1)
                except Exception as e:
                    self.logger.warning(f"Failed to leave {room_id}: {e}")

            await utils.answer(
                mx,
                self.strings.get("finished").format(count=count),
                edit_id=g,
            )
            return

        g = await utils.answer(mx, self.strings.get("starting").format(mode=payload.mode, target=payload.target))

        log_room = await self._get("log_room_id")
        joined_rooms = await mx.client.get_joined_rooms()
        count = 0

        checker_func = self.checkers[payload.mode]

        for room_id in joined_rooms:
            if room_id in (log_room, event.room_id):
                continue

                try:
                    should_leave = await checker_func(mx, room_id, payload.target)

                    if should_leave:
                        self.logger.warning(f"Leaving room {room_id} (Condition matched)")
                        await mx.client.leave_room(room_id)
                        count += 1

                        await asyncio.sleep(1)

                except Exception as e:
                    self.logger.warning(f"Failed to leave {room_id}: {e}")

        await utils.answer(mx, self.strings.get("finished").format(count=count), edit_id=g)

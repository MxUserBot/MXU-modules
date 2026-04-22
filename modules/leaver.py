import asyncio
from typing import Literal

from mautrix.types import EventType

from ...core import loader, utils


class Meta:
    name = "ChatMassacre"
    _cls_doc = "leaver chats"
    version = "3.1.0"
    tags = ["utility", "admin"]
    author = "@pasha:pashahatsune.pp.ua"


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
        mode: Literal["u", "n", "id"],
        target: str
    ):
        """<u/n/id> <target> - Mass leave rooms by User, Name, or IDs"""
        
        await utils.answer(mx, self.strings.get("starting").format(mode=mode, target=target))
        
        log_room = await mx._bot._db.get("core", "log_room_id")
        joined_rooms = await mx.client.get_joined_rooms()
        count = 0

        checker_func = self.checkers[mode]

        for room_id in joined_rooms:
            if room_id in (log_room, event.room_id):
                continue

            try:
                should_leave = await checker_func(mx, room_id, target)

                if should_leave:
                    self.logger.warning(f"Leaving room {room_id} (Condition matched)")
                    await mx.client.leave_room(room_id)
                    count += 1
                    
                    await asyncio.sleep(1)

            except Exception as e:
                raise e

        await utils.answer(mx, self.strings.get("finished").format(count=count))
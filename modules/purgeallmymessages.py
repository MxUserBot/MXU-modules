#			__  ____  ___   _               _           _   
#			|  \/  \ \/ / | | |___  ___ _ __| |__   ___ | |_ 
#			| |\/| |\  /| | | / __|/ _ \ '__| '_ \ / _ \| __|
#			| |  | |/  \| |_| \__ \  __/ |  | |_) | (_) | |_ 
#			|_|  |_/_/\_\\___/|___/\___|_|  |_.__/ \___/ \__| 
#
# 🔒      Licensed under the GNU AGPLv3
# 🌐 https://www.gnu.org/licenses/agpl-3.0.html


class Meta:
    name = "Purge Messages"
    description = "Purge Messages"
    version = "3.7.0"
    tags = ["messages"]
    author = "https://github.com/PashaHatsune"


import asyncio
from typing import Any

from mautrix.types import MessageEvent
from pydantic import BaseModel, Field, model_validator, ConfigDict

from mxc import utils
from mxc.types import MsgType
from .. import loader




class PurgePayload(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    
    target: str = Field(default="me")

    @model_validator(mode='before')
    @classmethod
    def parse_target(cls, v: Any):
        if not v:
            return {"target": "me"}
        
        val = v.strip().lower()
        if val in ("all", "*", "всё", "все"):
            return {"target": "all"}
        if val in ("me", "я", "мои"):
            return {"target": "me"}
            
        if val.startswith("@") and ":" in val:
            return {"target": val}
            
        return {"target": val}


class PurgeService:
    def __init__(self, mx, room_id: str, requester_id: str):
        self.mx = mx
        self.room_id = room_id
        self.requester_id = requester_id

    async def run(self, mode: str, exclude_id: str) -> int:
        count = 0
        token = None

        while True:
            resp = await utils.fetch_room_messages(
                self.mx,
                self.room_id,
                from_token=token, types={
                    MsgType.TEXT,
                    MsgType.IMAGE,
                    MsgType.VIDEO,
                    MsgType.AUDIO,
                    MsgType.FILE,
                    MsgType.EMOTE,
                    MsgType.NOTICE,
                    MsgType.STICKER,
                    MsgType.REACTION,
                },
            )
            chunk = resp.get("chunk", [])
            token = resp.get("end")

            if not chunk:
                break

            for evt in chunk:
                if evt.get("event_id") == exclude_id:
                    continue

                sender = evt.get("sender")
                if mode == "all" or sender == self._filter_sender(mode):
                    await self.mx.client.redact(self.room_id, evt["event_id"], reason="Purge")
                    count += 1

            if not token:
                break

            await asyncio.sleep(0.5)

        return count

    def _filter_sender(self, mode: str) -> str:
        if mode == "me":
            return self.requester_id
        return mode


@loader.tds
class PurgeAllMessagesModule(loader.Module):
    strings = {
        "starting": "🧹 | <b>Initiating purge protocol...</b><br>Target: <code>{target}</code>",
        "done": "✅ | <b>Cleanup finished!</b> Removed <code>{count}</code> messages from <code>{target}</code>.",
        "error": "❌ | <b>Critical failure!</b> Purge aborted. Check logs.",
    }

    @loader.command()
    async def purge(self, mx, event: MessageEvent, payload: PurgePayload):
        """[target/all/me/reply] - Absolute room cleanup engine."""
        
        reply = event.content.relates_to.in_reply_to if event.content.relates_to else None
        final_target = payload.target
        
        if reply and payload.target not in ("all", "*", "все", "всё"):
            try:
                replied_event = await mx.client.get_event(event.room_id, reply.event_id)
                final_target = replied_event.sender
            except Exception as e:
                raise e
        
        target_display = final_target
        await utils.answer(mx, self.strings["starting"].format(target=target_display))
        
        service = PurgeService(mx, event.room_id, mx.client.mxid)
        
        try:
            deleted_count = await service.run(
                mode=final_target,
                exclude_id=event.event_id,
            )
            await utils.answer(mx, self.strings["done"].format(
                count=deleted_count,
                target=target_display,
            ))
        except Exception as e:
            raise e

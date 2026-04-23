
import asyncio
from typing import List, Any

from mautrix.types import EventType, MessageEvent
from pydantic import BaseModel, Field, model_validator, ConfigDict

from ...core import loader, utils


class Meta:
    name = "Purge Messages"
    description = "Purge Messages"
    version = "3.6.0"
    tags = ["messages"]
    author = "@pasha:pashahatsune.pp.ua"


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
        self.valid_types = {
            EventType.ROOM_MESSAGE,
            EventType.ROOM_ENCRYPTED,
            EventType.REACTION,
        }


    async def collect_targets(
        self,
        mode: str,
        exclude_id: str
    ) -> List[str]:
        targets = []
        token = None
        
        filter_sender = None
        if mode == "me":
            filter_sender = self.requester_id
        elif mode != "all":
            filter_sender = mode 

        while True:
            resp = await utils.fetch_room_messages(self.mx, self.room_id, from_token=token)
            events = resp.get("chunk", [])
            token = resp.get("end")

            if not events:
                break

            for evt in events:
                eid = evt.get("event_id")
                sender = evt.get("sender")
                
                if eid == exclude_id:
                    continue

                if evt.get("type") not in [t.t for t in self.valid_types]:
                    continue

                if mode == "all" or sender == filter_sender:
                    targets.append(eid)

            if not token or not events:
                break
                
            await asyncio.sleep(0.5) 
            
        return targets

    async def execute(
        self, 
        event_ids: List[str]
    ) -> int:
        count = 0
        for eid in event_ids:
            try:
                await self.mx.client.redact(self.room_id, eid, reason="Purge")
                count += 1
                await asyncio.sleep(0.5) 
            except Exception as e:
                raise e
        return count



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
            targets = await service.collect_targets(
                mode=final_target, 
                exclude_id=event.event_id
            )
            
            deleted_count = await service.execute(targets)
            await utils.answer(mx, self.strings["done"].format(
                count=deleted_count, 
                target=target_display
            ))
            
        except Exception as e:
            raise e

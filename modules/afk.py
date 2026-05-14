import time

from mautrix.types import EventType, MessageEvent

from pydantic import Field

from ..core import loader
from mxc import utils

class Meta:
    name = "AFK"
    description = "AFK MODULE"
    version = "2.3.0"
    tags = ["utility"]


@loader.tds
class AFKModule(loader.Module):
    strings = {
        "afk_on": "<b>💤 | AFK Mode Activated</b><br>Reason: <code>{reason}</code>",
        "afk_off": "<b>✅ | AFK Mode Deactivated</b>",
        "afk_reply": "<b>💤 | User is currently AFK</b><br>Reason: <code>{reason}</code>",
    }

    config = {
        "enabled": loader.ConfigValue(False, "AFK status toggle", forbid=True),
        "reason": loader.ConfigValue(None, "AFK reason text"),
        "cooldown": loader.ConfigValue(60, "Auto-reply cooldown in seconds")
    }

    async def _matrix_start(self, mx):
        self._last_reply_times = {}

    @loader.command()
    async def afk(self, mx, event, reason: str = Field(default="Sleep", description="AFK reason")):
        """[reason] - Set AFK status"""
        status = reason
        self.config.set("enabled", True)
        self.config.set("reason", status)

        await utils.answer(mx, self.strings.get("afk_on").format(reason=status))

    @loader.command()
    async def unafk(self, mx, event):
        """Disable AFK mode"""
        self.config.set("enabled", False)
        await utils.answer(mx, self.strings.get("afk_off"))

    @loader.on(EventType.ROOM_MESSAGE)
    async def afk_handler(self, mx, event: MessageEvent):
        if not self.config["enabled"]:
            return

        if event.sender == mx.client.mxid:
            return
        
        if not await utils.is_dm(mx, event.room_id):
            return

        last_ts = self._last_reply_times.get(event.room_id, 0)
        if time.time() - last_ts < self.config["cooldown"]:
            return
        
        self._last_reply_times[event.room_id] = time.time()
        await utils.answer(
            mx.
            self.strings.get("afk_reply").format(reason=self.config["reason"])
        )
import time

from mautrix.types import EventType, MessageEvent

from ...core import loader, utils


class Meta:
    name = "AFK"
    _cls_doc = "AFK MODULE"
    version = "2.3.0"
    tags = ["utility"]


@loader.tds
class AFKModule(loader.Module):
    strings = {
        "afk_on": "<b>💤 | AFK Mode Activated</b><br>Reason: <code>{reason}</code>",
        "afk_off": "<b>✅ | AFK Mode Deactivated</b>",
        "afk_reply": "<b>💤 | User is currently AFK</b><br>Reason: <code>{reason}</code>",
        "default_reason": "Gone into the void."
    }

    config = {
        "enabled": loader.ConfigValue(False, "AFK status toggle"),
        "reason": loader.ConfigValue(strings.get("default_reason"), "AFK reason text"),
        "cooldown": loader.ConfigValue(60, "Auto-reply cooldown in seconds")
    }


    async def _matrix_start(self, mx):
        self._last_reply_times = {}


    @loader.command()
    async def afk(
        self,
        _,
        event,
        reason: str = None
    ) -> None:
        """<reason>"""

        status = reason or self.strings.get("default_reason")
        self.config.set("enabled", True)
        self.config.set("reason", status)

        await event.reply(self.strings.get("afk_on").format(reason=status))


    @loader.command()
    async def unafk(self, mx, event):
        """unafk"""
        self.config.set("enabled", False)
        await event.reply(self.strings.get("afk_off"))


    @loader.on(EventType.ROOM_MESSAGE)
    async def afk_handler(
        self,
        mx,
        event: MessageEvent
    ) -> None:
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
        await event.reply(
            self.strings.get("afk_reply").format(reason=self.config["reason"])
        )
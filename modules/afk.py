import time

from mautrix.types import EventType, MessageEvent

from pydantic import Field

from ..core import loader
from mxc import utils
from mxc.types.media import Image, DownloadMeta
from mxc.utils.events import get_reply_event

class Meta:
    name = "AFK"
    description = "AFK MODULE"
    version = "2.5.0"
    tags = ["utility"]


@loader.tds
class AFKModule(loader.Module):
    strings = {
        "afk_on": "<b>💤 | AFK Mode Activated</b><br>Reason: <code>{reason}</code>",
        "afk_off": "<b>✅ | AFK Mode Deactivated</b>",
        "afk_reply": "<b>💤 | User is currently AFK</b><br>Reason: <code>{reason}</code>",
        "afk_media_set": "<b>✅ | AFK media reply saved</b>",
        "afk_not_reply": "<b>⚠️ | Reply to a message</b>",
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
        self.config.set("enabled", True)
        self.config.set("reason", reason)
        await utils.answer(mx, self.strings.get("afk_on").format(reason=reason))

    @loader.command()
    async def unafk(self, mx, event):
        """Disable AFK mode"""
        self.config.set("enabled", False)
        await utils.answer(mx, self.strings.get("afk_off"))

    @loader.command()
    async def set_afk_reason(self, mx, event):
        """Reply to a message to set it as AFK reason with media"""
        replied = await get_reply_event(mx, event)
        if not replied:
            await utils.answer(mx, self.strings.get("afk_not_reply"))
            return

        text = replied.content.body or ""
        data = {"t": text}
        try:
            dl = await utils.download(mx, DownloadMeta(url=replied))
            if dl:
                mxc = await utils.upload(mx, Image(url=dl.url, mimetype=dl.mimetype, filename=dl.filename))
                data["mxc"] = mxc
                data["m"] = dl.mimetype
                data["f"] = dl.filename
        except Exception:
            pass

        self.config.set("reason", text)
        await self._set("afk_cache", data)
        await utils.answer(mx, self.strings.get("afk_media_set"))

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

        data = await self._get("afk_cache")
        if data and data.get("mxc"):
            img = Image(url=data["mxc"], mimetype=data["m"], filename=data["f"])
            await utils.answer(mx, text=data["t"], media=img)
            return

        await utils.answer(mx, self.strings.get("afk_reply").format(reason=self.config["reason"]))

import time

from ...core import loader, utils


class Meta:
    name = "AFK"
    _cls_doc = "AFK auto-reply for DMs"
    version = "1.0.0"
    tags = ["system"]


@loader.tds
class AFKModule(loader.Module):
    """AFK module (DM only)"""

    strings = {
        "name": "AFK",
        "afk_on": "<b>💤 AFK включен</b>\nПричина: <code>{}</code>",
        "afk_off": "<b>✅ AFK выключен</b>",
        "afk_reply": "<b>💤 Я сейчас AFK</b>\nПричина: <code>{}</code>",
    }


    async def _matrix_start(self, mx):
        self.afk = False
        self.reason = "не указана"
        self.last_reply = {}


    @loader.command()
    async def afk(self, mx, event):
        """<reason> - enable AFK"""

        args = event.content.body.split(maxsplit=1)
        reason = args[1] if len(args) > 1 else "не указана"

        self.afk = True
        self.reason = reason

        await utils.answer(mx, self.strings["afk_on"].format(reason))


    @loader.command()
    async def unafk(self, mx, event):
        """Disable AFK"""

        self.afk = False
        await utils.answer(mx, self.strings["afk_off"])


    async def _matrix_message(self, mx, event):
        if not self.afk:
            return

        if event.sender == mx.client.mxid:
            return

        room_id = event.room_id

        if not await event.is_dm(mx, room_id):
            return

        now = time.time()
        last = self.last_reply.get(room_id, 0)

        if now - last < 60:
            return

        self.last_reply[room_id] = now

        await utils.answer(
            mx,
            self.strings.get("afk_reply").format(self.reason), edit_id=None, event=event
        )

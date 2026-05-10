class Meta:
    name = "TestCron"
    description = "Test cron: toggle every-5s tick with .test"
    version = "1.0.0"
    tags = ["example", "cron"]


from mxc import utils
from .. import loader


@loader.tds
class TestCronModule(loader.Module):
    strings = {
        "started": "✅ | Крон запущен! Пишет каждые 5с.",
        "stopped": "⏹ | Крон остановлен.",
        "tick": "🔄 | это текст крона!",
    }

    _cron_active = False
    _room_id = None

    @loader.cron("5s")
    async def cron_tick(self, mx):
        """1"""
        if not self._cron_active or not self._room_id:
            return
        await utils.answer(mx, self.strings["tick"], room_id=self._room_id)

    @loader.command()
    async def test(self, mx, event):
        """1"""
        if not self._cron_active:
            self._cron_active = True
            self._room_id = event.room_id
            await utils.answer(mx, self.strings["started"], event=event)
        else:
            self._cron_active = False
            await utils.answer(mx, self.strings["stopped"], event=event)

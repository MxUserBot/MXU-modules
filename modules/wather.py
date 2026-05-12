"""
ДЕМО 6: WATCHER И EVENT HANDLER
Фичи:
- @loader.watcher — regex на все сообщения
- @loader.on — подписка на события (ROOM_MEMBER)
"""

from mautrix.types import EventType
from mxc import utils
from .. import loader


class Meta:
    name = "DemoWatcher"
    description = "демонстрация watcher и event handler"
    version = "1.0.0"
    tags = ["demo", "watcher"]


@loader.tds
class DemoWatcherModule(loader.Module):
    strings = {
        "spotted": "🔍 Замечен <b>{word}</b>!",
        "member_join": "👋 <b>{user}</b> зашёл в комнату",
        "member_leave": "🚪 <b>{user}</b> вышел из комнаты",
        "scream": "😂 КРИК ОБНАРУЖЕН!!!",
    }

    @loader.watcher(r"\b(?:бот|ботяра|robo)\b", security=loader.EVERYONE)
    async def on_bot_word(self, mx, event, match: str):
        """Реагирует на слова 'бот', 'ботяра', 'robo'"""
        await utils.answer(
            mx,
            self.strings["spotted"].format(word=match),
            event=event,
        )

    # @loader.watcher(r"[A-Z]{4,}", security=loader.EVERYONE)
    # async def on_caps(self, mx, event, match: str):
    #     """Реагирует на КРИК (4+ заглавных подряд)"""
    #     await utils.answer(
    #         mx,
    #         self.strings["scream"],
    #         event=event,
    #     )

    # @loader.on(EventType.ROOM_MEMBER)
    # async def on_member(self, mx, event):
    #     """Ловит события входа/выхода"""
    #     if event.content.membership == "join" and event.state_key != mx.client.mxid:
    #         await utils.answer(
    #             mx,
    #             self.strings["member_join"].format(user=event.state_key),
    #             event=event,
    #         )
    #     elif event.content.membership == "leave":
    #         await utils.answer(
    #             mx,
    #             self.strings["member_leave"].format(user=event.state_key),
    #             event=event,
    #         )

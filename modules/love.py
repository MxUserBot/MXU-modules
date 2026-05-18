import asyncio
import random
from pydantic import BaseModel

from mxc import utils
from .. import loader
from ..core.langs import Locales

R = "❤️"
W = "🤍"
BIG_SCROLL = ["🧡", "💚", "💙", "💜", "🖤"]

class Meta:
    name = "MatrixHearts"
    description = "nimated hearts in code"
    version = "1.1.0"
    tags = ["fun", "animation"]


class Strings(BaseModel):
    i: str
    love: str
    you: str


locales = Locales(
    ru=Strings(
        i="<code>❤️ Я</code>",
        love="<code>❤️ Я люблю</code>",
        you="<code>❤️ Я люблю тебя <3</code>",
    ),
    en=Strings(
        i="<code>❤️ I</code>",
        love="<code>❤️ I love</code>",
        you="<code>❤️ I love you <3</code>",
    ),
)


def get_heart(fill_color=R):
    heart_list = [
        W * 9,
        W * 2 + fill_color * 2 + W + fill_color * 2 + W * 2,
        W + fill_color * 7 + W,
        W + fill_color * 7 + W,
        W + fill_color * 7 + W,
        W * 2 + fill_color * 5 + W * 2,
        W * 3 + fill_color * 3 + W * 3,
        W * 4 + fill_color + W * 4,
        W * 9,
    ]
    return "<pre><code>" + "<br>".join(heart_list) + "</code></pre>"


@loader.tds
class MatrixHeartsModule(loader.Module):
    strings = locales

    @loader.command(aliases=["magic", "love"])
    async def hearts(self, mx, event):
        """hearts animation"""
        
        msg_id = await utils.answer(mx, get_heart(R), room_id=event.room_id)
        await asyncio.sleep(1.3)

        for color in [random.choice(BIG_SCROLL), random.choice(BIG_SCROLL)]:
            await utils.answer(mx, get_heart(color), edit_id=msg_id)
            await asyncio.sleep(1.3)

        full_red = "<pre><code>" + "<br>".join([R * 9] * 8) + "</code></pre>"
        await utils.answer(mx, full_red, edit_id=msg_id)
        await asyncio.sleep(1.3)

        for size in [5, 1]:
            shrink = "<pre><code>" + "<br>".join([R * size] * size) + "</code></pre>"
            await utils.answer(mx, shrink, edit_id=msg_id)
            await asyncio.sleep(1.3)

        await utils.answer(mx, self.strings.get("i"), edit_id=msg_id)
        await asyncio.sleep(1.3)
        
        await utils.answer(mx, self.strings.get("love"), edit_id=msg_id)
        await asyncio.sleep(1.3)
        
        await utils.answer(mx, self.strings.get("you"), edit_id=msg_id)

    @loader.command()
    async def heart_bomb(self, mx, event):
        """random hearts"""
        colors = [R, W, "🧡", "💛", "💚", "💙", "💜", "🤎", "🖤"]
        res = []
        for _ in range(7):
            res.append("".join(random.choices(colors, k=7)))
        
        await utils.answer(
            mx, 
            "<pre><code>" + "<br>".join(res) + "</code></pre>", 
            room_id=event.room_id
        )
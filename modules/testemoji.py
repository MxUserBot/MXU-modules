#			__  ____  ___   _               _           _   
#			|  \/  \ \/ / | | |___  ___ _ __| |__   ___ | |_ 
#			| |\/| |\  /| | | / __|/ _ \ '__| '_ \ / _ \| __|
#			| |  | |/  \| |_| \__ \  __/ |  | |_) | (_) | |_ 
#			|_|  |_/_/\_\\___/|___/\___|_|  |_.__/ \___/ \__| 
#
# 🔒      Licensed under the GNU AGPLv3
# 🌐 https://www.gnu.org/licenses/agpl-3.0.html


class Meta:
    name = "TestEmoji"
    description = "Inline emoji via mxc:// (static PNG)"
    version = "1.0.0"
    tags = ["test", "emoji"]


import base64
import re

from mautrix.types import MessageEvent

from mxc import utils
from .. import loader


LOVE_B64 = "iVBORw0KGgoAAAANSUhEUgAAABgAAAAYCAYAAADgdz34AAAA8klEQVR4nGNgGGzgraHrf1LUM5Ki+JWBC9xwsQt7GKlqwXMDZwyXS17YS1A/QQVP9J0IBonMxX2MZFnwUM+R6PCWv7SfkSQL7uk5kBSZIKB06QAjURbc1rUn2XAYUL18kBGvBTcoMBwGNJAsYWFAA3//U2w+A04fXNK2pZrpetcPM6JYcF7bhrpOZ2BgMLx6hJGFVkEDAzS3gBFEHNO0pI3pDFAf0Mr1CAsYaAdY6OOD/7SzgBHG2K5mSnVbPG+dZmSCcUC+IAZ73jrNSKxaEIBb4HP7DFEaGYh0DMg8lCBCButUjDCCK+jOOQy1xKqjKQAAh+y+rofpgZ4AAAAASUVORK5CYII="
THUMBS_B64 = "iVBORw0KGgoAAAANSUhEUgAAABQAAAAYCAYAAAD6S912AAAAZklEQVR4nGNgGAWDDjBSw5D/J1L+w9hM1DSMKgaiAyZquo6+Lvx/IuU/NheQZeB/JININZQJn2HkGMpIiWZsgIkSzXQxkIUahjBazGEcOl5mGrAwZEQKp4H1MiMWlxDrOryA3MIBANrmKXe6NZCfAAAAAElFTkSuQmCC"
SMILE_B64 = "iVBORw0KGgoAAAANSUhEUgAAABgAAAAYCAYAAADgdz34AAAAt0lEQVR4nMWVMQ6AMAhFSw/i5NLVI3hwj+Dq4uRFNDGpQYSCSvUnJibA+wGpDaGywJK0zt3KFrejWg9PwHeM4A3YYhS94FJt9IJLjEsH3oqSc1bql/25E8OsYge4mIJKsUsHHrOnyszvvgGnaWjYdy2GBbVGlA/evyPyUJT+IaX9t+RmptpBUky0+GFAu8CbkQonmcvHrBOU26ZkGBNdU9FAMpGMuP2nk6h+4cAvV2YwGlku/eraAIjTZVZHey0oAAAAAElFTkSuQmCC"

BASE_EMOJI: dict[str, tuple[str, str]] = {
    "aam":    (LOVE_B64,    "image/png"),
    "thumbs": (THUMBS_B64,  "image/png"),
    "smile":  (SMILE_B64,   "image/png"),
}


@loader.tds
class TestEmojiModule(loader.Module):
    strings = {
        "usage": "Usage: <code>.em {text with %shortcode%</code>",
    }

    def __init__(self):
        self._emoji_cache: dict[str, str] = {}

    async def _matrix_start(self, mx):
        await self._upload_emojis(mx)

    async def _upload_emojis(self, mx):
        self._emoji_cache = {}
        for sc, (b64, mime) in BASE_EMOJI.items():
            try:
                data = base64.b64decode(b64)
                mxc = await mx.client.upload_media(data, mime_type=mime)
                self._emoji_cache[sc] = str(mxc)
            except Exception:
                pass

    @loader.command()
    async def em(self, mx, event: MessageEvent, args: str = ""):
        """%shortcode% text - Send text with inline emoji"""
        if not args.strip():
            await event.reply(self.strings["usage"])
            return
        if not self._emoji_cache:
            await event.reply("❌ <b>Emoji not uploaded yet.</b>")
            return
        await utils.answer(
            mx, text=args.strip(),
            emoji_map=self._emoji_cache, room_id=event.room_id,
        )

    @loader.command()
    async def emlist(self, mx, event: MessageEvent):
        """List available emoji shortcodes"""
        codes = ", ".join(f"%{k}%" for k in BASE_EMOJI)
        lines = [f"<b>Available emoji:</b><br><code>{codes}</code>"]
        if self._emoji_cache:
            lines.append("<br><br><b>mxc URLs:</b>")
            for sc, url in self._emoji_cache.items():
                lines.append(f"<br><code>%{sc}%</code> → <code>{url}</code>")
        else:
            lines.append("<br><br>❌ <b>Not uploaded.</b> Use .em to trigger")
        await utils.answer(mx, text="".join(lines), room_id=event.room_id)

    @loader.command()
    async def emojirefresh(self, mx, event: MessageEvent):
        """Re-upload all emoji to homeserver"""
        await event.reply("🔄 <b>Re-uploading emoji...</b>")
        await self._upload_emojis(mx)
        count = len(self._emoji_cache)
        await event.reply(f"✅ <b>Uploaded {count} static PNG emoji</b>")

#			__  ____  ___   _               _           _   
#			|  \/  \ \/ / | | |___  ___ _ __| |__   ___ | |_ 
#			| |\/| |\  /| | | / __|/ _ \ '__| '_ \ / _ \| __|
#			| |  | |/  \| |_| \__ \  __/ |  | |_) | (_) | |_ 
#			|_|  |_/_/\_\\___/|___/\___|_|  |_.__/ \___/ \__| 
#
# 🔒      Licensed under the GNU AGPLv3
# 🌐 https://www.gnu.org/licenses/agpl-3.0.html


class Meta:
    name = "Rule34"
    description = "API wrapper for Rule34."
    version = "2.0.0"
    tags = ["18+", "api"]
    author = "https://github.com/PashaHatsune"


import asyncio
from typing import Dict, Optional

from pydantic import BaseModel
from mautrix.types import MessageEvent

from mxc import utils
from mxc.types import EmojiButton, Image
from mxc.utils.keyboard import EmojiKeyBoard
from .. import loader


class Rule34Config(BaseModel):
    api_key: str
    user_id: str

    @classmethod
    def from_raw(cls, raw: str):
        if ":" not in raw:
            raise ValueError("Invalid format. Expected api_key:user_id")
        k, u = raw.split(":", 1)
        return cls(api_key=k, user_id=u)


class Rule34Engine:
    @staticmethod
    async def fetch_posts(
        tags: Optional[str], 
        auth: Rule34Config, 
        strings: Dict[str, str]
    ) -> list[str]:
        params = {
            "page": "dapi",
            "s": "post",
            "q": "index",
            "tags": tags or "",
            "limit": 20,
            "json": 1,
            "user_id": auth.user_id,
            "api_key": auth.api_key
        }

        try:
            data = await utils.request(
                url="https://api.rule34.xxx/index.php",
                params=params
            )

            if not data or not isinstance(data, list):
                raise ValueError(strings["no_results"])

            _IMAGE_EXTS = {"jpg", "jpeg", "png", "webp"}
            urls = [
                item["file_url"] for item in data
                if "file_url" in item and item["file_url"].lower().rsplit(".", 1)[-1] in _IMAGE_EXTS
            ]
            if not urls:
                raise ValueError(strings["no_results"])

            return urls

        except Exception as e:
            if str(e) == strings["no_results"]:
                raise
            raise RuntimeError(strings["api_error"]) from e


@loader.tds
class Rule34Module(loader.Module):
    strings = {
        "warning": "<b>⚠️ | 18+ CONTENT WARNING | ⚠️</b><br><b>Sequence initiated. Safe delay enforced (5s).</b>",
        "used_tag": "🏷 | <b>Tags:</b> <code>{tag}</code>",
        "error": "❌ | <b>API Failure:</b> <code>{err}</code>",
        "no_results": "❌ | <b>Query Failure:</b> No results found for specified tags.",
        "api_error": "❌ | <b>Network Failure:</b> Rule34 API is unreachable.",
        "config_err": "❌ | <b>Configuration Failure:</b> Key must be in <code>api_key:user_id</code> format."
    }

    config = {
        "api_key": loader.ConfigValue(
            default=None,
            description="Rule34 API Credentials in format api_key:user_id",
            required=True
        ),
        "safety_delay": loader.ConfigValue(
            default=5,
            description="Mandatory delay before sending NSFW content",
            validator=lambda x: isinstance(x, int) and x >= 0
        )
    }


    @loader.command()
    async def rule34(
        self,
        mx,
        event: MessageEvent, 
        tags: str = None
    ) -> None:
        """<tags> | Fetch images from Rule34"""

        try:
            auth = Rule34Config.from_raw(self.config["api_key"])
        except ValueError:
            return await utils.answer(mx, self.strings["config_err"])

        try:
            urls = await Rule34Engine.fetch_posts(tags, auth, self.strings)

            warn_id = await utils.answer(mx, self.strings["warning"])
            await asyncio.sleep(self.config["safety_delay"])

            async def on_page(ctx):
                page = ctx.data["page"]
                if ctx.payload == "prev":
                    page = (page - 1) % len(urls)
                else:
                    page = (page + 1) % len(urls)
                ctx.data["page"] = page

                markup = EmojiKeyBoard(
                    rows=[[
                        EmojiButton(emoji="⬅️", data="prev"),
                        EmojiButton(emoji="➡️", data="next"),
                    ]],
                    callback=on_page,
                    data=ctx.data,
                    allowed_senders=ctx.sender,
                    remove_clicked=False,
                )

                await ctx.close()
                await utils.answer(
                    ctx.mx,
                    media=Image(
                        url=urls[page],
                        caption=self.strings["used_tag"].format(
                            tag=utils.escape_html(tags or "none"),
                        ),
                    ),
                    edit_id=ctx.message_id,
                    reply_markup=markup,
                )

            markup = EmojiKeyBoard(
                rows=[[
                    EmojiButton(emoji="⬅️", data="prev"),
                    EmojiButton(emoji="➡️", data="next"),
                ]],
                callback=on_page,
                data={"page": 0},
                remove_clicked=False,
            )

            await utils.answer(
                mx,
                media=Image(
                    url=urls[0],
                    caption=self.strings["used_tag"].format(
                        tag=utils.escape_html(tags or "none"),
                    ),
                ),
                edit_id=warn_id,
                reply_markup=markup,
            )

        except Exception as e:
            raise e

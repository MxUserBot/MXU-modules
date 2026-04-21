import random
import asyncio
from typing import Dict, Optional

from pydantic import BaseModel
from mautrix.types import MessageEvent

from ...core import loader, utils


class Meta:
    name = "Rule34"
    _cls_doc = "API wrapper for Rule34."
    version = "2.0.0"
    tags = ["18+", "api"]


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
    async def fetch_random_post(
        tags: Optional[str], 
        auth: Rule34Config, 
        strings: Dict[str, str]
    ) -> str:
        params = {
            "page": "dapi",
            "s": "post",
            "q": "index",
            "tags": tags or "",
            "limit": 20, # Fetch more to increase entropy
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

            urls = [item["file_url"] for item in data if "file_url" in item]
            if not urls:
                raise ValueError(strings["no_results"])

            return random.choice(urls)

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
        tags: str = ""
    ) -> None:
        """<tags> | Fetch a random image from Rule34"""
        try:
            auth = Rule34Config.from_raw(self.config["api_key"])
        except ValueError:
            return await utils.answer(mx, self.strings["config_err"])

        try:
            url = await Rule34Engine.fetch_random_post(tags, auth, self.strings)

            await utils.answer(mx, self.strings["warning"])
            await asyncio.sleep(self.config["safety_delay"])

            await utils.send_image(
                mx,
                room_id=event.room_id,
                url=url,
                caption=self.strings["used_tag"].format(tag=utils.escape_html(tags or "none"))
            )

        except Exception as e:
            raise e

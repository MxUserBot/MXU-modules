#			__  ____  ___   _               _           _   
#			|  \/  \ \/ / | | |___  ___ _ __| |__   ___ | |_ 
#			| |\/| |\  /| | | / __|/ _ \ '__| '_ \ / _ \| __|
#			| |  | |/  \| |_| \__ \  __/ |  | |_) | (_) | |_ 
#			|_|  |_/_/\_\\___/|___/\___|_|  |_.__/ \___/ \__| 
#
# 🔒      Licensed under the GNU AGPLv3
# 🌐 https://www.gnu.org/licenses/agpl-3.0.html


class Meta:
    name = "TGStickerPort"
    description = "Telegram sticker/emoji migration engine. NOT SUPPORT TGS"
    version = "3.6.0-TURBO"
    tags =["media", "ports"]
    dependencies = ["av", "pillow"]


import io
import re
import uuid
import asyncio
from typing import Any, Dict, List, Tuple, Optional

import av
from PIL import Image
from pydantic import BaseModel, Field, model_validator, ConfigDict
from mautrix.types import MessageEvent

from mxc import utils
from .. import loader
from mxc.types import Sticker


class TGPackPayload(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    pack_name: str = Field(min_length=1)

    @model_validator(mode='before')
    @classmethod
    def validate_link(cls, v: Any):
        if isinstance(v, str):
            match = re.search(r"t\.me/(?:addstickers|addemoji)/([A-Za-z0-9_]+)", v, re.IGNORECASE)
            if not match:
                raise ValueError("Invalid link")
            return {"pack_name": match.group(1)}
        return v


class StickerItem(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    body: str
    mxc_url: str
    width: int
    height: int
    size: int
    shortcode: str


class TGStickerEngine:
    SEMAPHORE = asyncio.Semaphore(2) 

    @staticmethod
    def _convert_to_webp(
        file_bytes: bytes,
        is_video: bool = False
    ) -> bytes:
        if is_video:
            out = io.BytesIO()
            frames =[]
            try:
                container = av.open(io.BytesIO(file_bytes))
                for frame in container.decode(video=0):
                    img = frame.to_image().convert("RGBA")
                    frames.append(img)
                    if len(frames) >= 45:
                        break
                container.close()
            except Exception as e:
                raise RuntimeError(f"AV decoding failed: {e}")

            if not frames:
                raise ValueError("No video frames")

            frames[0].save(
                out,
                format="WEBP",
                save_all=True,
                append_images=frames[1:],
                duration=40,
                loop=0,
                quality=75,
                method=4 
            )
            return out.getvalue()
        else:
            try:
                img = Image.open(io.BytesIO(file_bytes)).convert("RGBA")
                out = io.BytesIO()
                img.save(out, format="WEBP", lossless=True, method=4)
                return out.getvalue()
            except Exception as e:
                raise RuntimeError(f"Static conversion failed: {e}")


    @classmethod
    async def _process_single_sticker(
        cls,
        mx,
        token,
        sticker,
        pack_name,
        i,
        logger,
        proxy: str = None
    ) -> Optional[StickerItem]:
        req_kwargs = {"proxy": proxy} if proxy else {}

        async with cls.SEMAPHORE:
            try:
                file_id = sticker["file_id"]
                is_video = sticker.get("is_video", False)
                is_animated = sticker.get("is_animated", False)

                if is_animated and not is_video:
                    if "thumbnail" in sticker:
                        file_id = sticker["thumbnail"]["file_id"]
                        is_video = False
                    else:
                        return None

                f_data = await utils.request(
                    url=f"https://api.telegram.org/bot{token}/getFile?file_id={file_id}",
                    method="GET",
                    return_type="json",
                    **req_kwargs
                )
                
                if not f_data.get("ok"): 
                    return None
                file_path = f_data["result"]["file_path"]

                raw_bytes = await utils.request(
                    url=f"https://api.telegram.org/file/bot{token}/{file_path}",
                    method="GET",
                    return_type="bytes",
                    **req_kwargs
                )

                processed_bytes = await asyncio.to_thread(
                    cls._convert_to_webp,
                    raw_bytes,
                    is_video
                )

                mxc_url = await utils.upload(
                    mx,
                    processed_bytes,
                    mime_type="image/webp",
                )

                return StickerItem(
                    body=sticker.get("emoji", "✨"),
                    mxc_url=mxc_url,
                    width=sticker.get("width", 512),
                    height=sticker.get("height", 512),
                    size=len(processed_bytes),
                    shortcode=sticker.get("custom_emoji_id") or f"tg_{pack_name}_{i}",
                )

            except Exception as e:
                logger.exception(f"Failed to process sticker {i}: {e}")
                return None


    @classmethod
    async def process_pack(
        cls, mx, token: str, pack_name: str, strings: Dict[str, str], logger: Any, proxy: str = None
    ) -> Tuple[str, List[StickerItem]]:
        req_kwargs = {"proxy": proxy} if proxy else {}

        data = await utils.request(
            url=f"https://api.telegram.org/bot{token}/getStickerSet?name={pack_name}",
            method="GET",
            return_type="json",
            **req_kwargs
        )
        
        if not data.get("ok"):
            raise ValueError(
                strings["api_err"].format(
                    err=data.get("description", "Unknown")
                )
            )

        pack_data = data["result"]
        
        tasks =[
            cls._process_single_sticker(mx, token, s, pack_name, i, logger, proxy)
            for i, s in enumerate(pack_data["stickers"], 1)
        ]
        
        results = await asyncio.gather(*tasks)
        processed_items =[r for r in results if r is not None]

        if not processed_items:
            raise ValueError(strings["empty_pack"])

        return pack_data["title"], processed_items


@loader.tds
class TGStickerPortModule(loader.Module):
    strings = {
        "start": "⏳ | <b>Importing.. Pls wait :)</b>",
        "done": "✅ | <b>Successfully imported {count} items!</b>",
        "bad_url": "❌ | <b>Invalid URL:</b> Use t.me/addstickers/... or t.me/addemoji/...",
        "api_err": "❌ | <b>Telegram API Error:</b> <code>{err}</code>",
        "empty_pack": "❌ | <b>Processing Error:</b> No supported media assets found.",
    }

    config = {
        "tg_token": loader.ConfigValue(
            default="",
            description="Telegram Bot Token from t.me/BotFather",
            required=True,
        ),
        "proxy": loader.ConfigValue(
            default="",
            description="Proxy URL for Telegram API (e.g. http://127.0.0.1:1080). Leave empty if not needed.",
        ),
        "preview_after_import": loader.ConfigValue(
            default=True,
            description="Send first 3 stickers as preview after successful import",
        )
    }

    @loader.command()
    async def port(self, mx, event: MessageEvent, link: TGPackPayload):
        """<link> - Port Telegram stickers/emojis. TGS not support!
        👍 | Format: 
        https://t.me/addstickers/....
        https://t.me/addemoji/...
        """
        status_id = await utils.answer(
            mx,
            self.strings["start"]
        )

        try:
            title, items = await TGStickerEngine.process_pack(
                mx,
                self.config["tg_token"],
                link.pack_name,
                self.strings,
                self.logger,
                self.config["proxy"]
            )

            images_content = {
                item.shortcode: {
                    "body": item.body,
                    "url": item.mxc_url,
                    "info": {
                        "mimetype": "image/webp",
                        "w": item.width,
                        "h": item.height,
                        "size": item.size,
                    },
                    "usage": ["sticker", "emoticon"],
                } for item in items
            }

            pack_id = f"tg_{link.pack_name.lower()}_{uuid.uuid4().hex[:6]}"
            await mx.client.send_state_event(
                room_id=event.room_id,
                event_type="im.ponies.room_emotes",
                content={
                    "pack": {
                        "display_name": f"TG: {title}",
                        "usage": ["sticker", "emoticon"],
                        "avatar_url": items[0].mxc_url,
                    },
                    "images": images_content,
                },
                state_key=pack_id,
            )

            await utils.answer(
                 mx,
                 self.strings["done"].format(
                     count=len(items)
                 ),
                 edit_id=status_id
             )

            if self.config.get("preview_after_import"):
                 for item in items[:3]:
                     await utils.answer(
                         mx,
                         media=Sticker(
                             url=item.mxc_url,
                             w=item.width,
                             h=item.height,
                             mimetype="image/webp",
                             size=item.size
                         ),
                         edit_id=None
                     )
                    
                 await utils.answer(mx, f"<b>TG: {title}</b>")

        except Exception as e:
            raise e

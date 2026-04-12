import aiohttp
from mautrix.types import (
    MessageEvent, ImageInfo, 
)
from ...core import loader
from mautrix.client import Client


class Meta:
    name = "CatGirlModule"
    _cls_doc = "Отправляет фото кошко девочек"
    version = "1.0.0"
    tags = ["api"]


@loader.tds
class CatGirlModule(loader.Module):
    strings = {"error": "Ошибка API"}

    @loader.command()
    async def catgirl(self, mx: Client, event: MessageEvent):
        """Отправляет фото кошко-девочки"""

        async with aiohttp.ClientSession() as s:
            async with s.get("https://api.nekosia.cat/api/v1/images/catgirl") as r:
                if r.status != 200: 
                    return await mx.send_text(event.room_id, self.strings["error"])
                data = await r.json()
                url = data["image"]["original"]["url"]
            
            async with s.get(url) as img:
                image_bytes = await img.read()


        await mx.client.send_image(
            room_id=event.room_id,
            file_bytes=image_bytes,
            info=ImageInfo(
                mimetype="image/png",
                size=len(image_bytes)
            ),
            file_name="catgirl.png",
            caption="Моя кошко-девочка"
        )

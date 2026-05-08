from ..core import loader, utils
from ..core.exceptions import UsageError
from ..core.utils.media_types import Image


class Meta:
    name = "CatGirl"
    description = "via Nekosia API."
    version = "2.0.0"
    author = "@pasha:pashahatsune.pp.ua"
    tags = ["api", "media"]


@loader.tds
class CatGirlModule(loader.Module):
    strings = {
        "fetching": "🐱 | <b>Locating a tactical catgirl...</b>",
        "error": "❌ | <b>API failure:</b> <code>{err}</code>",
        "caption": "✨ | <b>Catgirl ID:</b> <code>{id}</code>"
    }

    @loader.command()
    async def catgirl(
        self,
        mx,
        event
    ):
        """Summon a random catgirl picture"""
        ids = await utils.answer(mx, self.strings.get("fetching"))

        api_url = "https://api.nekosia.cat/api/v1/images/catgirl"

        try:
            data = await utils.request(api_url)
            
            img_url = data["image"]["original"]["url"]
            img_id = data["id"]


            image_bytes = await utils.request(
                url=img_url,
                return_type="bytes"
            )

            await utils.answer(
                mx,
                media=Image(
                    url=image_bytes,
                    caption=self.strings.get("caption").format(id=img_id)
                ),
                edit_id=ids

            )

        except (TypeError, KeyError, IndexError):
            raise UsageError()
        except Exception as e:
            raise e
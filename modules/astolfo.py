from .. import loader, utils
from ..core.utils.media_types import Image


class Meta:
    name = "Astolfo"
    description = "Astolfo pic from astolfo.rocks."
    version = "2.0.0"
    tags = ["api", "media"]


@loader.tds
class AstolfoModule(loader.Module):
    strings = {
        "fetching": "🌸 | <b>Summoning a wild Astolfo...</b>",
        "error": "❌ | <b>Deployment failure:</b> <code>{err}</code>",
        "caption": "✨ | <b>Asset ID:</b> <code>{id}</code> | <b>Rating:</b> <code>{rating}</code>"
    }


    @loader.command()
    async def astolfo(
        self,
        mx,
        event,
        rating: str = "safe"
    ):
        """<rating> - Summon a random Astolfo picture"""


        ids = await utils.answer(mx, self.strings.get("fetching"))

        api_url = "https://astolfo.rocks/api/images/random"

        try:
            data = await utils.request(api_url, params={"rating": rating.lower()})
            
            img_id = data["id"]
            ext = data["file_extension"]
            img_url = f"https://astolfo.rocks/astolfo/{img_id}.{ext}"


            image_bytes = await utils.request(
                url=img_url,
                return_type="bytes"
            )

            await utils.answer(
                mx,
                media=Image(
                    url=image_bytes,
                    caption=self.strings.get("caption").format(id=img_id, rating=rating),
                    filename="astolfo.png",
                    mimetype="image/png"
                ),
                edit_id=ids
            )

        except Exception as e:
            raise e

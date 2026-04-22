from ...core import loader, utils
from ...core.exceptions import UsageError


class Meta:
    name = "CatGirl"
    _cls_doc = "Strategic deployment of feline-humanoid assets via Nekosia API."
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
        await utils.answer(mx, self.strings.get("fetching"))

        api_url = "https://api.nekosia.cat/api/v1/images/catgirl"

        try:
            data = await utils.request(api_url)
            
            img_url = data["image"]["original"]["url"]
            img_id = data["id"]

            await utils.send_image(
                mx, 
                event, 
                url=img_url, 
                caption=self.strings.get("caption").format(id=img_id)
            )

        except (TypeError, KeyError, IndexError):
            raise UsageError()
        except Exception as e:
            raise e
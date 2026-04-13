from ...core import loader, utils


class Meta:
    name = "CatGirlModule"
    _cls_doc = "Отправляет фото кошко девочек"
    version = "1.0.1"
    tags = ["api"]


@loader.tds
class CatGirlModule(loader.Module):
    strings = {"error": "Ошибка API"}

    @loader.command()
    async def catgirl(self, mx, event):
        """Отправляет фото кошко-девочки"""

                
        api_url = "https://api.nekosia.cat/api/v1/images/catgirl"
        data = await utils.request(api_url, params={"rating": "safe"})


        url = data["image"]["original"]["url"]
        


        await utils.send_image(mx, event, url, file_name=f"{data['id']}.jpg")

from ...core import loader, utils


class Meta:
    name = "AstolfoModule"
    _cls_doc = "Скидывает случайные изображения Астольфо с astolfo.rocks"
    version = "1.1"
    tags = ["api"]


@loader.tds
class AstolfoModule(loader.Module):
    strings = {"error": "Ошибка при получении няшности"}

    @loader.command()
    async def astolfo(self, mx, event):
        """[rating] - Получить фото"""
        
        api_url = "https://astolfo.rocks/api/images/random"
        data = await utils.request(api_url, params={"rating": "safe"})
        
        if not data:
            return await utils.answer(event, self.strings["error"])

        img_url = f"https://astolfo.rocks/astolfo/{data['id']}.{data['file_extension']}"
        
        image_bytes = await utils.request(img_url, return_type="bytes")

        await utils.send_image(mx, event, image_bytes, file_name=f"{data['id']}.jpg")

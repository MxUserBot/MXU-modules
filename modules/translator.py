from googletrans import Translator
from ...core import loader


class Meta:
    name = "Translator"
    _cls_doc = "google translator"
    version = "2.0.0"
    tags = ["utility"]


@loader.tds
class TranslatorModule(loader.Module):
    strings = {
        "result": "<b><u>[Translator]</u></b><br><code>{result}</code>"
    }

    @loader.command()
    async def tr(
        self,
        mx,
        event,
        lang: str = "en",
        text: str = None
    ) -> None:
        """<lang> <lang: ru/ua/ja/etc> <text/reply> | Translate text"""
        
        async with Translator() as tr_obj:
            res = await tr_obj.translate(text, dest=lang)
            await event.reply(self.strings.get("result").format(result=res.text))
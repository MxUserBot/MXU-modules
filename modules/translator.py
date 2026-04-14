from ...core import utils, loader
from googletrans import Translator
from mautrix.client import Client
from mautrix.types import MessageEvent

class Meta:
    name = "TranslatorModule"
    _cls_doc = "Позволяет переводить текст из одного языка на другой"
    version = "1.0.0"
    tags = ["translates"]

@loader.tds
class TranslatorModule(loader.Module):
    strings = {
        "no_args": "Укажи язык: .tr en текст",
        "result": "<b><u>[Translator]</u></b> | {result}"
    }

    @loader.command()
    async def tr(self, mx: Client, event: MessageEvent):
        """Перевод текста. Использование: .tr <язык> <текст> или реплаем: .tr <язык>"""
        try:
            raw = await utils.get_args_raw(mx, event)
            
            if not raw:
                return await utils.answer(mx, self.strings["no_args"])

            parts = raw.split(maxsplit=1)
            lang = parts[0].lower().strip()
            text = parts[1].strip() if len(parts) > 1 else ""

            if not text:
                reply_text = await utils.get_reply_text(mx, event)
                
                if reply_text is False:
                    return await utils.answer(mx, "❌ Укажи текст или ответь на сообщение.")
                elif reply_text is None:
                    return
                
                text = reply_text

            if not text:
                return await utils.answer(mx, "❌ Сообщение пустое.")

            self.logger.info(f"[TR] Translating to {lang}: {text[:50]}...")

            async with Translator() as tr_obj:
                try:
                    result = await tr_obj.translate(text, dest=lang)
                except Exception as e:
                    self.logger.error(f"Ошибка выбора языка: {e}")
                    result = await tr_obj.translate(text, dest="en")

            await utils.answer(mx, self.strings.get("result").format(result=result.text))

        except Exception as global_e:
            self.logger.error(f"Глобальная ошибка команды: {global_e}")
            try:
                await utils.answer(mx, f"⚠️ <b>Произошла критическая ошибка:</b> {global_e}")
            except:
                pass
from ...core import utils, loader
from googletrans import Translator
from googletrans.models import Translated

from mautrix.client import Client
from mautrix.types import MessageEvent



@loader.tds
class MatrixModule(loader.Module):
    strings = {
        "name": "TranslatorModule",
        "_cls_doc": "Перевод текста по reply или команде",
        "no_args": "Укажи язык: .tr en текст",
        "no_text": "Нет текста для перевода.",
        "bad_lang": "Неверный язык.",
        "error": "Ошибка перевода.",
        "result": "<b><u>[Trasnlator]</u></b> | {result}"
    }

    @loader.command()
    async def tr(self, mx: Client, event: MessageEvent):
        """1"""
        try:
            raw = await utils.get_args_raw(mx, event)
            print(raw)

            if not raw:
                return await mx.answer(self.strings["no_args"])

            parts = raw.split(maxsplit=1)

            lang = parts[0].lower().strip().replace(".", "")
            print(lang)

            # # защита от мусора
            # if lang not in VALID_LANGS:
            #     # если пользователь не указал язык, считаем что он хотел en
            #     if len(lang) > 5 or any(c.isdigit() for c in lang):
            #         lang = "en"
            #     else:
            #         return await mx.answer(self.strings["bad_lang"])

            text = parts[1].strip() if len(parts) > 1 else ""

            if not text:
                return await mx.answer(self.strings["no_text"])

            self.logger.info(f"[TR] lang={lang} text={text[:80]!r}")

            async with Translator() as tr:
                try:
                    result: Translated = await tr.translate(
                        text=text,
                        dest=lang
                    )
                except Exception:
                    result: Translated = await tr.translate(
                        text=text,
                        dest="en"
                    )

            await mx.answer(self.strings.get("result").format(
                result=result.text
            ))

        except Exception as e:
            self.logger.exception(f"[TR] failed: {e}")
            await mx.answer(self.strings["error"])
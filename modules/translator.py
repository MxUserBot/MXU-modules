#			__  ____  ___   _               _           _   
#			|  \/  \ \/ / | | |___  ___ _ __| |__   ___ | |_ 
#			| |\/| |\  /| | | / __|/ _ \ '__| '_ \ / _ \| __|
#			| |  | |/  \| |_| \__ \  __/ |  | |_) | (_) | |_ 
#			|_|  |_/_/\_\\___/|___/\___|_|  |_.__/ \___/ \__| 
#
# 🔒      Licensed under the GNU AGPLv3
# 🌐 https://www.gnu.org/licenses/agpl-3.0.html


class Meta:
    name = "Translator"
    description = "google translator"
    version = "2.0.0"
    tags = ["utility"]
    author = "https://github.com/PashaHatsune"
    dependencies = ["googletrans"]


from googletrans import Translator
from mxc import utils
from .. import loader


@loader.tds
class TranslatorModule(loader.Module):
    strings = {
        "result": "<b><u>[Translator]</u></b><br><code>{result}</code>",
        "no_reply": "⚠️ <b>Failed to get reply:</b> no decryption key.",
        "need_text": "❌ <b>Specify text or reply to a message.</b>"
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
        
        if not text:
            text = await event.get_reply_text()
        if text is None:
            return await utils.answer(mx, self.strings["no_reply"], event=event)
        if not text:
            return await utils.answer(mx, self.strings["need_text"], event=event)

        async with Translator() as tr_obj:
            res = await tr_obj.translate(text, dest=lang)
            await utils.answer(mx, self.strings["result"].format(result=res.text), event=event)
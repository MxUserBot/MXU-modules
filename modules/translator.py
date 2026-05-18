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


from typing import Optional

from googletrans import Translator
from mxc import utils
from mxc.exceptions import UsageError
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
        text: Optional[str] = None
    ) -> None:
        """<lang> <lang: ru/ua/ja/etc> <text/reply/eid> | Translate text"""
        
        if text and text.startswith("$"):
            try:
                ctx = await utils.get_context_events(mx, event.room_id, text, limit=0)
                if ctx:
                    text = ctx[-1].content.body
            except Exception:
                pass

        if not text:
            try:
                reply_evt = await utils.get_reply_event(mx, event)
                if reply_evt:
                    text = reply_evt.content.body
            except Exception:
                pass

        if not text:
            raise UsageError(self.strings["need_text"])

        async with Translator() as tr_obj:
            res = await tr_obj.translate(text, dest=lang)
            await utils.answer(mx, self.strings["result"].format(result=res.text), event=event)
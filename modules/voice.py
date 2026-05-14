#			__  ____  ___   _               _           _   
#			|  \/  \ \/ / | | |___  ___ _ __| |__   ___ | |_ 
#			| |\/| |\  /| | | / __|/ _ \ '__| '_ \ / _ \| __|
#			| |  | |/  \| |_| \__ \  __/ |  | |_) | (_) | |_ 
#			|_|  |_/_/\_\\___/|___/\___|_|  |_.__/ \___/ \__| 
#
# 🔒      Licensed under the GNU AGPLv3
# 🌐 https://www.gnu.org/licenses/agpl-3.0.html


class Meta:
    name = "VoiceTranscriber"
    description = "Transcribe voice messages with OpenAI Whisper"
    version = "1.0.0"
    tags = ["voice", "ai"]


import aiohttp

from mautrix.types import EventType, MessageEvent, MessageType

from mxc import utils
from mxc.exceptions import UsageError
from mxc.types import DownloadMeta
from .. import loader


_AUDIO_EXTS = frozenset({".ogg", ".mp3", ".wav", ".m4a", ".webm", ".oga", ".flac", ".mp4"})


@loader.tds
class VoiceModule(loader.Module):
    config = {
        "openai_key": loader.ConfigValue(
            "NONE",
            "OpenAI API key for Whisper transcription",
            required=True,
        ),
        "auto_transcribe": loader.ConfigValue(
            False,
            "Auto-transcribe voice messages in allowed rooms",
        ),
        "auto_rooms": loader.ConfigValue(
            [],
            "Room IDs for auto-transcription (comma-separated)",
        ),
    }

    strings = {
        "processing": "🎤 <b>Transcribing voice message...</b>",
        "no_reply": "❌ <b>Reply to a voice message.</b>",
        "no_voice": "❌ <b>That message is not a voice message.</b>",
        "result": "🎤 <b>Transcription:</b><br><i>{text}</i>",
        "error": "❌ <b>Transcription failed:</b> <code>{err}</code>",
        "not_configured": (
            "❌ <b>OpenAI API key not configured.</b> "
            "Use <code>{prefix}cfg voicetranscriber openai_key YOUR_KEY</code>"
        ),
    }

    def _is_voice(self, content) -> bool:
        msgtype = getattr(content, "msgtype", None)
        if msgtype == MessageType.AUDIO:
            return True
        body = (getattr(content, "body", "") or "").lower()
        return any(body.endswith(ext) for ext in _AUDIO_EXTS)

    @loader.command()
    async def voice(self, mx, event: MessageEvent):
        """[lang] — Transcribe replied voice message. Optionally specify language (e.g. en, ru)."""
        key = self.config.get("openai_key")
        if not key or key == "NONE":
            prefix = await utils.get_prefix(mx)
            raise UsageError(self.strings["not_configured"].format(prefix=prefix))

        reply = await utils.get_reply_event(mx, event)
        if not reply:
            raise UsageError(self.strings["no_reply"])

        if not self._is_voice(reply.content):
            raise UsageError(self.strings["no_voice"])

        status_id = await utils.answer(mx, self.strings["processing"])

        try:
            data, filename, mimetype, _ = await utils.download(mx, meta=DownloadMeta(url=reply))
        except Exception:
            raise UsageError(self.strings["no_voice"])

        args = await utils.get_args(mx, event)
        lang = args[0] if args else None

        try:
            text = await self._transcribe(data, filename, mimetype, key, lang)
            await utils.answer(mx, self.strings["result"].format(text=text), edit_id=status_id)
        except Exception as e:
            await utils.answer(mx, self.strings["error"].format(err=str(e)), edit_id=status_id)

    @loader.on(EventType.ROOM_MESSAGE)
    async def auto_handler(self, mx, event: MessageEvent):
        if not self.config.get("auto_transcribe"):
            return
        rooms = self.config.get("auto_rooms")
        if not rooms or event.room_id not in rooms:
            return

        key = self.config.get("openai_key")
        if not key or key == "NONE":
            return

        if not self._is_voice(event.content):
            return

        try:
            data, filename, mimetype, _ = await utils.download(mx, meta=DownloadMeta(url=event))
        except Exception:
            return

        try:
            text = await self._transcribe(data, filename, mimetype, key)
            if text:
                await utils.answer(mx, self.strings["result"].format(text=text), event=event)
        except Exception:
            pass

    async def _transcribe(
        self,
        audio_data: bytes,
        filename: str,
        mimetype: str,
        api_key: str,
        lang: str = None,
    ) -> str:
        form = aiohttp.FormData()
        form.add_field("file", audio_data, filename=filename, content_type=mimetype or "audio/ogg")
        form.add_field("model", "whisper-1")
        if lang:
            form.add_field("language", lang)

        headers = {"Authorization": f"Bearer {api_key}"}

        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api.openai.com/v1/audio/transcriptions",
                headers=headers,
                data=form,
            ) as resp:
                if resp.status != 200:
                    err_text = await resp.text()
                    raise RuntimeError(f"API error {resp.status}: {err_text[:300]}")
                result = await resp.json()
                return result.get("text", "")

import asyncio
import yt_dlp
from mautrix.types import (
    MessageEvent, EventType, MessageType, 
    MediaMessageEventContent, AudioInfo
)

from ...core import loader, utils


class Meta:
    name = "YTMusic"
    _cls_doc = "YouTube Music Downloader."
    version = "1.2.1"
    tags = ["downloader", "media"]
    author = "@pasha:pashahatsune.pp.ua"


@loader.tds
class YTMusicModule(loader.Module):
    strings = {
        "searching": "🔍 | <b>Searching:</b> <code>{query}</code>",
        "processing": "📥 | <b>Downloading...</b>",
        "error": "❌ <b>Error:</b> <code>{err}</code>",
        "not_found": "❌ <b>Song not found.</b>"
    }

    async def _run_yt_dlp(self, loop, ydl, query):
        return await loop.run_in_executor(None, lambda: ydl.extract_info(query, download=True))

    @loader.command()
    async def ytm(self, mx, event: MessageEvent, query: str):
        """<query/link/reply> | Download audio from YouTube"""
        
        status_id = await utils.answer(mx, self.strings.get("searching").format(query=query))
        print(status_id)
        
        file_id = f"ytm_{event.event_id}"
        out_tmpl = str(utils.COMM_DIR / f"{file_id}.%(ext)s")
        
        ydl_opts = {
            "format": "bestaudio/best",
            "outtmpl": out_tmpl,
            "noplaylist": True,
            "quiet": True,
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }],
        }

        search_query = query if query.startswith("http") else f"ytsearch1:{query}"

        try:
            await mx.client.set_typing(event.room_id, timeout=15000)
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info_dict = await self._run_yt_dlp(asyncio.get_event_loop(), ydl, search_query)
                
                if "entries" in info_dict:
                    if not info_dict["entries"]:
                        return await utils.answer(mx, self.strings.get("not_found"))
                    info = info_dict["entries"][0]
                else:
                    info = info_dict

                await utils.answer(mx, self.strings.get("processing"), edit_id=status_id)

                title = info.get("title", "Track")
                uploader = info.get("uploader", "Artist")
                duration = info.get("duration", 0)
                final_path = utils.COMM_DIR / f"{file_id}.mp3"

                if not final_path.exists():
                    raise FileNotFoundError("Conversion failed.")

                with open(final_path, "rb") as f:
                    file_bytes = f.read()

                mxc = await mx.client.upload_media(file_bytes, mime_type="audio/mpeg", filename=f"{title}.mp3")

                content = MediaMessageEventContent(
                    msgtype=MessageType.AUDIO,
                    body=f"{uploader} - {title}.mp3",
                    url=mxc,
                    info=AudioInfo(mimetype="audio/mpeg", size=len(file_bytes), duration=int(duration * 1000))
                )

                await mx.client.send_message(event.room_id, content)

                await mx.client.redact(event.room_id, status_id)

        except Exception as e:
            raise e
        
        finally:
            await mx.client.set_typing(event.room_id, timeout=0)
            for ext in ["mp3", "webm", "m4a", "part"]:
                await utils.safe_remove(f"{file_id}.{ext}")
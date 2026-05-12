#			__  ____  ___   _               _           _   
#			|  \/  \ \/ / | | |___  ___ _ __| |__   ___ | |_ 
#			| |\/| |\  /| | | / __|/ _ \ '__| '_ \ / _ \| __|
#			| |  | |/  \| |_| \__ \  __/ |  | |_) | (_) | |_ 
#			|_|  |_/_/\_\\___/|___/\___|_|  |_.__/ \___/ \__| 
#
# 🔒      Licensed under the GNU AGPLv3
# 🌐 https://www.gnu.org/licenses/agpl-3.0.html


class Meta:
    name = "YTMusic"
    description = "YouTube Music Downloader."
    version = "1.2.1"
    tags = ["downloader", "media"]
    dependencies = ["yt-dlp"]
    author = "https://github.com/PashaHatsune"


import asyncio
import yt_dlp

from mxc import utils
from mxc.types import Audio
from .. import loader


@loader.tds
class YTMusicModule(loader.Module):
    strings = {
        "searching": "🔍 | <b>Searching:</b> <code>{query}</code>",
        "processing": "📥 | <b>Downloading...</b>",
        "error": "❌ <b>Error:</b> <code>{err}</code>",
        "not_found": "❌ <b>Song not found.</b>",
        "no_reply": "⚠️ <b>Failed to get reply:</b> no decryption key."
    }

    async def _run_yt_dlp(self, loop, ydl, query):
        return await loop.run_in_executor(None, lambda: ydl.extract_info(query, download=True))

    @loader.command()
    async def ytm(self, mx, event, query: str = ""):
        """<query/link/reply> | Download audio from YouTube"""
        
        if not query:
            query = await event.get_reply_text()
        if query is None:
            return await utils.answer(mx, self.strings["no_reply"], event=event)
        if not query:
            return

        status_id = await utils.answer(mx, self.strings.get("searching").format(query=query))

        
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

            await utils.answer(
                mx,
                text=f"{uploader} - {title}",
                media=Audio(
                    url=file_bytes,
                    filename=f"{uploader} - {title}.mp3",
                    duration=duration * 1000,
                    size=len(file_bytes)
                ),
                edit_id=status_id
            )


        except Exception as e:
            raise e
        
        finally:
            await mx.client.set_typing(event.room_id, timeout=0)
            for ext in ["mp3", "webm", "m4a", "part"]:
                await utils.safe_remove(f"{file_id}.{ext}")

#			__  ____  ___   _               _           _   
#			|  \/  \ \/ / | | |___  ___ _ __| |__   ___ | |_ 
#			| |\/| |\  /| | | / __|/ _ \ '__| '_ \ / _ \| __|
#			| |  | |/  \| |_| \__ \  __/ |  | |_) | (_) | |_ 
#			|_|  |_/_/\_\\___/|___/\___|_|  |_.__/ \___/ \__| 
#
# 🔒      Licensed under the GNU AGPLv3
# 🌐 https://www.gnu.org/licenses/agpl-3.0.html


class Meta:
    name = "TikTokDL"
    description = " TikTok downloader"
    version = "3.2.1"
    tags = ["media", "api"]
    author = "https://github.com/PashaHatsune"


import re
import uuid
import asyncio
from typing import Any, Dict

from pydantic import BaseModel, Field, model_validator, ConfigDict
from mautrix.types import MessageEvent, MessageType, MediaMessageEventContent, VideoInfo

from mxc import utils
from mxc.types import Video
from .. import loader


class TikTokPayload(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    url: str = Field(min_length=1)

    @model_validator(mode='before')
    @classmethod
    def extract_url(cls, v: Any):
        if isinstance(v, str):
            match = re.search(r"https?://(?:www\.|vm\.|vt\.)?tiktok\.com/[^\s]+", v)
            if not match:
                raise ValueError("No valid TikTok link detected")
            return {"url": match.group(0)}
        return v


class TikTokEngine:
    @staticmethod
    async def fetch_video_data(url: str, strings: Dict[str, str]) -> str:
        api_url = f"https://www.tikwm.com/api?url={url}"
        try:
            res = await utils.request(api_url)
            if not res or "data" not in res:
                raise ValueError(strings["api_error"].format(err="Empty response"))
            
            play_url = res["data"].get("play")
            if not play_url:
                raise ValueError(strings["api_error"].format(err="Missing play URL"))
            
            return play_url
        except Exception as e:
            raise RuntimeError(strings["api_error"].format(err=str(e)))


    @staticmethod
    async def transcode_video(raw_bytes: bytes, strings: Dict[str, str]) -> bytes:
        job_id = uuid.uuid4().hex[:8]
        in_file = f"tt_raw_{job_id}.mp4"
        out_file = f"tt_final_{job_id}.mp4"

        in_path = await utils.safe_save(raw_bytes, in_file)
        out_path = str(utils._get_safe_path(out_file))

        try:
            process = await asyncio.create_subprocess_exec(
                "ffmpeg",
                "-i", in_path,
                "-c:v", "libx264", "-preset", "ultrafast", "-crf", "28",
                "-c:a", "aac", "-b:a", "128k", "-y", out_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                err_log = stderr.decode()
                raise RuntimeError(f"FFmpeg error {process.returncode}: {err_log[:150]}")

            def read_result():
                with open(out_path, "rb") as f:
                    return f.read()
            
            return await asyncio.to_thread(read_result)

        except Exception as e:
            raise RuntimeError(strings["error"].format(err=f"Pipeline failure: {e}"))
        finally:
            await utils.safe_remove(in_file)
            await utils.safe_remove(out_file)


@loader.tds
class TikTokDLModule(loader.Module):
    strings = {
        "downloading": "⏳ |<b>Acquiring TikTok asset...</b>",
        "processing": "⚙️ | <b>Transcoding sequence (Safe Storage)...</b>",
        "uploading": "📤 | <b>Dispatching to Matrix infrastructure...</b>",
        "api_error": "❌ | <b>API Protocol Breach:</b> <code>{err}</code>",
        "error": "❌ | <b>Operational Failure:</b> <code>{err}</code>"
    }

    @loader.command()
    async def tt(self, mx, event: MessageEvent, link: TikTokPayload):
        """<link> - Download TikTok video"""
        url = link.url
        status_id = await utils.answer(mx, self.strings["downloading"])

        try:
            video_url = await TikTokEngine.fetch_video_data(url, self.strings)

            video_bytes = await utils.request(video_url, return_type="bytes")
            if not video_bytes:
                raise ValueError("Received null payload from source.")

            await utils.answer(mx, self.strings["processing"], edit_id=status_id)
            final_video = await TikTokEngine.transcode_video(video_bytes, self.strings)

            await utils.answer(mx, self.strings["uploading"], edit_id=status_id)
            mxc = await mx.client.upload_media(final_video, mime_type="video/mp4")

            await utils.answer(
                mx, 
                media=Video(
                    url=mxc,
                    mimetype="video/mp4", 
                    size=len(final_video),
                    w=600,
                    h=900

                ),
                edit_id=status_id
            )
            
            # await mx.client.redact(event.room_id, status_id)
            if status_id != event.event_id:
                await mx.client.redact(event.room_id, event.event_id)

        except Exception as e:
            raise e

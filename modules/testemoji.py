#			__  ____  ___   _               _           _   
#			|  \/  \ \/ / | | |___  ___ _ __| |__   ___ | |_ 
#			| |\/| |\  /| | | / __|/ _ \ '__| '_ \ / _ \| __|
#			| |  | |/  \| |_| \__ \  __/ |  | |_) | (_) | |_ 
#			|_|  |_/_/\_\\___/|___/\___|_|  |_.__/ \___/ \__| 
#
# 🔒      Licensed under the GNU AGPLv3
# 🌐 https://www.gnu.org/licenses/agpl-3.0.html


class Meta:
    name = "TestEmoji"
    description = "Inline emoji via mxc:// (static + animated)"
    version = "0.6.0"
    tags = ["test", "emoji"]


import base64
import gzip
import re
import tempfile
import subprocess
from io import BytesIO

from PIL import Image

from mautrix.types import MessageEvent, TextMessageEventContent, Format

from mxc import utils
from .. import loader
from rlottie_python import LottieAnimation


LOVE_B64 = "iVBORw0KGgoAAAANSUhEUgAAABgAAAAYCAYAAADgdz34AAAA8klEQVR4nGNgGGzgraHrf1LUM5Ki+JWBC9xwsQt7GKlqwXMDZwyXS17YS1A/QQVP9J0IBonMxX2MZFnwUM+R6PCWv7SfkSQL7uk5kBSZIKB06QAjURbc1rUn2XAYUL18kBGvBTcoMBwGNJAsYWFAA3//U2w+A04fXNK2pZrpetcPM6JYcF7bhrpOZ2BgMLx6hJGFVkEDAzS3gBFEHNO0pI3pDFAf0Mr1CAsYaAdY6OOD/7SzgBHG2K5mSnVbPG+dZmSCcUC+IAZ73jrNSKxaEIBb4HP7DFEaGYh0DMg8lCBCButUjDCCK+jOOQy1xKqjKQAAh+y+rofpgZ4AAAAASUVORK5CYII="
THUMBS_B64 = "iVBORw0KGgoAAAANSUhEUgAAABQAAAAYCAYAAAD6S912AAAAZklEQVR4nGNgGAWDDjBSw5D/J1L+w9hM1DSMKgaiAyZquo6+Lvx/IuU/NheQZeB/JININZQJn2HkGMpIiWZsgIkSzXQxkIUahjBazGEcOl5mGrAwZEQKp4H1MiMWlxDrOryA3MIBANrmKXe6NZCfAAAAAElFTkSuQmCC"
SMILE_B64 = "iVBORw0KGgoAAAANSUhEUgAAABgAAAAYCAYAAADgdz34AAAAt0lEQVR4nMWVMQ6AMAhFSw/i5NLVI3hwj+Dq4uRFNDGpQYSCSvUnJibA+wGpDaGywJK0zt3KFrejWg9PwHeM4A3YYhS94FJt9IJLjEsH3oqSc1bql/25E8OsYge4mIJKsUsHHrOnyszvvgGnaWjYdy2GBbVGlA/evyPyUJT+IaX9t+RmptpBUky0+GFAu8CbkQonmcvHrBOU26ZkGBNdU9FAMpGMuP2nk6h+4cAvV2YwGlku/eraAIjTZVZHey0oAAAAAElFTkSuQmCC"
BEATING_B64 = "H4sICMwlH2MAA21lbnVfYWRkX2dpZi5qc29uANVZ3W/bNhD/VwI9UwS/Kfptw4Y+DSjQYS+GUWi2U3tJbENSshZB/vfdHSlZkpWkSd0uRWNJR94deb/74Em9z+6yWWZ54C5j2WWVzZxg2faQzeC2h5ss4OHfbGalYtkm3Xc3IHSz3t1+LFerj5+2lyC7Wq1IqKzrdVNns/mCZdfll3WFz/fd9HYHd8my5ks2M0lTfV3WG1BRVzR1BRL32R4vJclcwbBA2c/wIB9YVg3m2hkBM4fBzFxZx/AnFpEH9n4NV2Ash4xBMPhr2WTHVic2Gdnusy0OAMtccMPSD6TAmrlk8G8BQvsjDywdf4kH1oBVgKehpREbVRhujGHtHUwFhrOuVMSVtCy49QVr799hJemSUV5wpRRr7+1SwKLME3YnB7jkAHTUPiK1KQ/rGEoYOtmnCgJm20Sf7GJs0QRFUnLiVT3wMlk6n5Of6bogu0YjdziSQxrAD0bhwdH4Mptdltf1+iGF0kOK3vdls7mQsOjNDqhffvv194u/1stmX118wD1f5Bfvqv3tARg2q05FsqJuMlLcD0XBhQ5KWld45xTgbKV3xovCW2/IHXEDuvXKaZKYB8rZ3lTgwds4aWHyehlz4R+6/X1DbGTNh6baX62n7XlXlYfNdgkWRa5Jkxp0zOEku4qC+8URuVH69VKvl3RpEs3C4DiaPZn/7nE8PCq9mhJCpOpyasa2/v2zKnf15b66yTA6aYgcShjtDoTgMhWXhGQKvwkAx4GwOC22dSwNy4Z0kEYEd1BA1bCAbpf73duun62+iZx/LOM3Zf1HiV5rqts1gAnP9ftqf1hXzTZVgu3uLgEJ8/vVGqAoMfqap9P+66+nBeJFslRKNGQwZjEMg39Hz3RFgcGzlEhxayHX5wpoF5j2XAaPggaS2QF2zvEiIIe0lluhYURyZRTKWK61g0LPpZKpeCGMD8ckeyQ+ML0+P5YpFGzoFIh9DN0fXJSlVlwVngXJNdktPVeipc9fovu9ytEE9bwJ6EMjJcvh8BMhurSwSGqniCeXXHg3aTFN2fhIAgylTSRBHSPdk6EmdeCFKpgruKKFpAxcKNsf8FwIiQPGRwwdhBcMBMAwDkA3aBXzAKq2vQEpAlfaP4uzeh3OaoyzfhpnA9srEgK5xAiwBB6EvDARPcUdWAZTynRwAYZSYPciVaSEwX5HkqnAwrXpYTvEG5whO2ccvdR3Ya4hQsHTiutitB04xHCX6HRNkPejRQWN4SG9JlIEQ6TwkTSBSKt7bo9xkkwqTIwuGelh8J3EiVc8BMfgJqhcQN3QUOW7KDFQRywd2fY42/qfzT1WJGwfoSQRLXnhPNAYSogNKDYS6pGw3BdpwFEXaGHCpwEPvhEG1tBpAHQEcGuRaGOBBiBtiGs4WWCqW9px4BYwosxHm53mbWF4vhLo10WoHkeo+ZZihpaKXqom+muzzLz1hnOy2cSm6BrlfkzTGbq+5ZGOZaLpfPRN7/hGNPU+dHwXSm9COr7ltM3r1HvWCzVCTkeV8AoOv7OoDFFlsCzY7gXNj7b+Zjtv+w2dNztXz5JjpVIsN7yQWLngQWmDR4C08QyA0ib65T6yMpKLCoCToVis71GgY4/6W/XExlCEmsGx7qg6b3UTH4tbSqdGVH4sTN1qkbfdxnCPUXlvtbiNzsgRBsczqlWejOx2ko822vY+xxUSjq2l+RCG4cu6h/YZ+mRFx6GzcKwBnhraZBqA9hjKG7Oa+0Aegb4YSBf5B8SYdaxrsBIReUdF1rzjTbryThmtlLdL5SPyhD0/0Zj3Vzzp6n/6LxL6fzkkUpvzsk8T5zolxNlPieLJQ6KApKXrSw8KN3VQmLd+UNgnP9GoVx8Ur206fsrvXC6BKCZB1N8FxFcl5RvH0T+Joznn98IFfi+rruJ/viwe/gOpnAAO5hkAAA=="


def _tgs_render_frames(data: bytes, size=(24, 24), max_frames=30) -> list[Image.Image] | None:
    try:
        decomp = gzip.decompress(data)
        anim = LottieAnimation.from_data(data=decomp.decode("utf-8"))
        total = anim.lottie_animation_get_totalframe()

        seen: set[bytes] = set()
        frames: list[Image.Image] = []
        for i in range(total):
            img = anim.render_pillow_frame(frame_num=i, width=size[0], height=size[1])
            raw = img.tobytes()
            if raw not in seen:
                seen.add(raw)
                frames.append(img)
                if len(frames) >= max_frames:
                    break
        return frames
    except Exception:
        return None


def _tgs_to_apng(data: bytes, size=(24, 24), max_frames=30) -> bytes | None:
    frames = _tgs_render_frames(data, size, max_frames)
    if not frames:
        return None
    try:
        src_fps = 60
        buf = BytesIO()
        frames[0].save(
            buf, format="PNG", save_all=True,
            append_images=frames[1:], duration=int(1000 / src_fps), loop=0,
        )
        return buf.getvalue()
    except Exception:
        return None


def _tgs_to_gif(data: bytes, size=(24, 24), max_frames=30) -> bytes | None:
    frames = _tgs_render_frames(data, size, max_frames)
    if not frames:
        return None
    try:
        frames_rgba = [f.convert("RGBA") for f in frames]
        buf = BytesIO()
        frames_rgba[0].save(
            buf, format="GIF", save_all=True,
            append_images=frames_rgba[1:], duration=int(1000 / 60),
            loop=0, disposal=2, transparency=0,
        )
        return buf.getvalue()
    except Exception:
        return None


def _tgs_to_webp(data: bytes, size=(24, 24), max_frames=30) -> bytes | None:
    frames = _tgs_render_frames(data, size, max_frames)
    if not frames:
        return None
    try:
        buf = BytesIO()
        frames[0].save(
            buf, format="WEBP", save_all=True,
            append_images=frames[1:], duration=int(1000 / 60),
            loop=0, lossless=True,
        )
        return buf.getvalue()
    except Exception:
        return None


def _tgs_to_webm(data: bytes, size=(24, 24), max_frames=30) -> bytes | None:
    frames = _tgs_render_frames(data, size, max_frames)
    if not frames or not frames:
        return None
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            paths = []
            for i, f in enumerate(frames):
                p = f"{tmpdir}/f{i:04d}.png"
                f.save(p)
                paths.append(p)
            out = f"{tmpdir}/out.webm"
            subprocess.run(
                [
                    "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
                    "-framerate", "60", "-i", f"{tmpdir}/f%04d.png",
                    "-c:v", "libvpx-vp9", "-pix_fmt", "yuva420p",
                    "-an", out,
                ],
                check=True,
            )
            with open(out, "rb") as f:
                return f.read()
    except Exception:
        return None


BASE_EMOJI: dict[str, tuple[str, str]] = {
    "aam":    (LOVE_B64,    "image/png"),
    "thumbs": (THUMBS_B64,  "image/png"),
    "smile":  (SMILE_B64,   "image/png"),
    "beat":   (BEATING_B64, "image/webp"),
}


SHORTCODE_RE = re.compile(r":([a-zA-Z0-9_-]+):")


def _render_video_emojis(text: str, emoji_map: dict[str, str]) -> str:
    def _repl(m):
        sc = m.group(1)
        url = emoji_map.get(sc)
        if not url:
            return m.group(0)
        return (
            f'<video src="{url}" '
            f'loop autoplay muted playsinline '
            f'style="display: inline-block; vertical-align: -2px; height: 32px;">'
            f'</video>'
        )
    return SHORTCODE_RE.sub(_repl, text)


@loader.tds
class TestEmojiModule(loader.Module):
    strings = {
        "usage": "Usage: <code>.em {text with :shortcode:</code>",
    }

    def __init__(self):
        self._emoji_cache: dict[str, str] = {}

    async def _matrix_start(self, mx):
        await self._upload_emojis(mx)

    async def _upload_emojis(self, mx):
        self._emoji_cache = {}
        for sc, (b64, mime) in BASE_EMOJI.items():
            try:
                data = base64.b64decode(b64)
                if data[:2] == b"\x1f\x8b":
                    webp = _tgs_to_webp(data)
                    if webp:
                        data, mime = webp, "image/webp"
                mxc = await mx.client.upload_media(data, mime_type=mime)
                self._emoji_cache[sc] = str(mxc)
            except Exception:
                pass

    @loader.command()
    async def em(self, mx, event: MessageEvent, args: str = ""):
        """:shortcode: text - Send text with inline emoji"""
        if not args.strip():
            await event.reply(self.strings["usage"])
            return
        if not self._emoji_cache:
            await event.reply("❌ <b>Emoji not uploaded yet.</b>")
            return
        await utils.answer(
            mx, text=args.strip(),
            emoji_map=self._emoji_cache, room_id=event.room_id,
        )

    @loader.command()
    async def emlist(self, mx, event: MessageEvent):
        """List available emoji shortcodes"""
        codes = ", ".join(f":{k}:" for k in BASE_EMOJI)
        lines = [f"<b>Available emoji:</b><br><code>{codes}</code>"]
        if self._emoji_cache:
            lines.append("<br><br><b>mxc URLs:</b>")
            for sc, url in self._emoji_cache.items():
                lines.append(f"<br><code>:{sc}:</code> → <code>{url}</code>")
        else:
            lines.append("<br><br>❌ <b>Not uploaded.</b> Use .em to trigger")
        await utils.answer(mx, text="".join(lines), room_id=event.room_id)

    @loader.command()
    async def emojirefresh(self, mx, event: MessageEvent):
        """Re-upload all emoji to homeserver"""
        await event.reply("🔄 <b>Re-uploading emoji...</b>")
        await self._upload_emojis(mx)
        count = len(self._emoji_cache)
        await event.reply(f"✅ <b>Uploaded {count} emoji (static + animated)</b>")

    @loader.command()
    async def emgif(self, mx, event: MessageEvent, args: str = ""):
        """:shortcode: text - Send as GIF"""
        if not args.strip():
            await event.reply("Usage: <code>.emgif {text with :shortcode:</code>")
            return
        data = base64.b64decode(BEATING_B64)
        gif_data = _tgs_to_gif(data)
        if not gif_data:
            await event.reply("❌ GIF conversion failed")
            return
        mxc = await mx.client.upload_media(gif_data, mime_type="image/gif")
        mxc_url = str(mxc)
        await utils.answer(
            mx, text=args.strip(),
            emoji_map={"beat": mxc_url}, room_id=event.room_id,
        )

    @loader.command()
    async def emapng(self, mx, event: MessageEvent, args: str = ""):
        """:shortcode: text - Send as APNG with image/apng MIME"""
        if not args.strip():
            await event.reply("Usage: <code>.emapng {text with :shortcode:</code>")
            return
        data = base64.b64decode(BEATING_B64)
        apng_data = _tgs_to_apng(data)
        if not apng_data:
            await event.reply("❌ APNG conversion failed")
            return
        mxc = await mx.client.upload_media(apng_data, mime_type="image/apng")
        mxc_url = str(mxc)
        await utils.answer(
            mx, text=args.strip(),
            emoji_map={"beat": mxc_url}, room_id=event.room_id,
        )

    @loader.command()
    async def emwebm(self, mx, event: MessageEvent, args: str = ""):
        """:shortcode: text - Send as WebM <video> tag with alpha"""
        if not args.strip():
            await event.reply("Usage: <code>.emwebm {text with :shortcode:</code>")
            return
        data = base64.b64decode(BEATING_B64)
        webm_data = _tgs_to_webm(data)
        if not webm_data:
            await event.reply("❌ WebM conversion failed")
            return
        mxc = await mx.client.upload_media(webm_data, mime_type="video/webm")
        mxc_url = str(mxc)
        formatted = _render_video_emojis(args.strip(), {"beat": mxc_url})
        content = TextMessageEventContent(
            body=args.strip(),
            msgtype="m.text",
            format=Format.HTML,
            formatted_body=formatted,
        )
        await mx.client.send_message(event.room_id, content)

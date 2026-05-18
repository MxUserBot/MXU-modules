#			__  ____  ___   _               _           _   
#			|  \/  \ \/ / | | |___  ___ _ __| |__   ___ | |_ 
#			| |\/| |\  /| | | / __|/ _ \ '__| '_ \ / _ \| __|
#			| |  | |/  \| |_| \__ \  __/ |  | |_) | (_) | |_ 
#			|_|  |_/_/\_\\___/|___/\___|_|  |_.__/ \___/ \__| 
#
# 🔒      Licensed under the GNU AGPLv3
# 🌐 https://www.gnu.org/licenses/agpl-3.0.html


class Meta:
    name = "Quote"
    description = "Element-style quotes"
    version = "2.3.0"
    tags = ["image", "media"]
    dependencies = ["pillow"]
    author = "https://github.com/PashaHatsune"


import io
import asyncio
import textwrap
from typing import Optional, Tuple

from pydantic import BaseModel, ConfigDict
from mautrix.types import MessageEvent, MessageType
from PIL import Image, ImageDraw, ImageFont, ImageOps

from mxc import utils
from mxc.exceptions import UsageError
from mxc.types import DownloadMeta, Image as MXImage
from .. import loader
from ..core import utils as cutils


MEDIA_TYPES = frozenset({
    MessageType.IMAGE, MessageType.VIDEO, MessageType.STICKER,
})


class QuoteEntry(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    sender_name: str
    text: str
    avatar_bytes: Optional[bytes] = None
    nested_name: Optional[str] = None
    nested_text: Optional[str] = None
    media_bytes: Optional[bytes] = None


class QuoteEngine:
    MAX_W, MIN_W, X_OFFSET, PADDING = 600, 200, 75, 18
    SEP_GAP = 8

    @classmethod
    def _avail_media_w(cls, final_w):
        return max(1, final_w - cls.X_OFFSET - cls.PADDING - 10)

    @classmethod
    def _measure(cls, tmp_draw, entries, f_name, f_text, f_reply_name, f_reply_text):
        content_w = 0
        entry_heights = []

        for entry in entries:
            main_lines = []
            for line in entry.text.splitlines():
                main_lines.extend(textwrap.wrap(line, width=45))

            name_w = tmp_draw.textbbox((0, 0), entry.sender_name, f_name)[2]
            max_line_w = 0
            for line in main_lines:
                max_line_w = max(max_line_w, tmp_draw.textbbox((0, 0), line, f_text)[2])

            nested_w = 0
            if entry.nested_name:
                nw_name = tmp_draw.textbbox((0, 0), entry.nested_name, f_reply_name)[2]
                nw_text = tmp_draw.textbbox((0, 0), (entry.nested_text or "")[:70], f_reply_text)[2]
                nested_w = max(nw_name, nw_text) + 15

            content_w = max(content_w, name_w, max_line_w, nested_w)

            h = 24
            if entry.nested_name:
                h += 48
            h += len(main_lines) * 22 + 8
            entry_heights.append(h)

        final_w = max(cls.MIN_W, min(content_w + cls.X_OFFSET + cls.PADDING, cls.MAX_W))

        for i, entry in enumerate(entries):
            if entry.media_bytes:
                try:
                    img = Image.open(io.BytesIO(entry.media_bytes))
                    ratio = min(cls._avail_media_w(final_w) / img.width, 1)
                    entry_heights[i] += int(img.height * ratio) + 6
                except Exception:
                    pass

        total_h = cls.PADDING + sum(entry_heights) + cls.SEP_GAP * (len(entries) - 1) + cls.PADDING

        return final_w, total_h, entry_heights

    @classmethod
    def render(cls, entries: list[QuoteEntry], fonts, strings) -> Tuple[bytes, int, int]:
        try:
            f_name = ImageFont.truetype(io.BytesIO(fonts["bold"]), 18)
            f_text = ImageFont.truetype(io.BytesIO(fonts["regular"]), 17)
            f_reply_name = ImageFont.truetype(io.BytesIO(fonts["bold"]), 14)
            f_reply_text = ImageFont.truetype(io.BytesIO(fonts["regular"]), 14)
        except Exception as e:
            raise RuntimeError(strings["font_render_err"]) from e

        tmp_draw = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
        final_w, total_h, entry_heights = cls._measure(tmp_draw, entries, f_name, f_text, f_reply_name, f_reply_text)

        canvas = Image.new("RGBA", (final_w, total_h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(canvas)
        draw.rounded_rectangle([0, 0, final_w, total_h], radius=18, fill=(21, 25, 30, 255))

        curr_y = cls.PADDING
        for i, entry in enumerate(entries):
            if entry.avatar_bytes:
                try:
                    av = Image.open(io.BytesIO(entry.avatar_bytes)).convert("RGBA")
                    av = ImageOps.fit(av, (48, 48), centering=(0.5, 0.5))
                    mask = Image.new("L", (48, 48), 0)
                    ImageDraw.Draw(mask).ellipse((0, 0, 48, 48), fill=255)
                    av.putalpha(mask)
                    canvas.alpha_composite(av, (15, curr_y))
                except:
                    draw.ellipse([15, curr_y, 15 + 48, curr_y + 48], fill=(50, 55, 60))
            else:
                draw.ellipse([15, curr_y, 15 + 48, curr_y + 48], fill=(50, 55, 60))

            draw.text((cls.X_OFFSET, curr_y), entry.sender_name, font=f_name, fill=(255, 178, 239, 255))
            inner_y = curr_y + 28

            if entry.nested_name:
                draw.rectangle([cls.X_OFFSET, inner_y, cls.X_OFFSET + 2, inner_y + 38], fill=(255, 178, 239, 255))
                draw.text((cls.X_OFFSET + 12, inner_y), entry.nested_name, font=f_reply_name, fill=(255, 178, 239, 180))
                n_crop = (entry.nested_text or "")[:75]
                if len(entry.nested_text or "") > 75:
                    n_crop += "..."
                draw.text((cls.X_OFFSET + 12, inner_y + 18), n_crop, font=f_reply_text, fill=(141, 151, 165, 255))
                inner_y += 46

            main_lines = []
            for line in entry.text.splitlines():
                main_lines.extend(textwrap.wrap(line, width=45))

            for line in main_lines:
                draw.text((cls.X_OFFSET, inner_y), line, font=f_text, fill=(225, 225, 225, 255))
                inner_y += 22

            if entry.media_bytes:
                try:
                    media_img = Image.open(io.BytesIO(entry.media_bytes)).convert("RGBA")
                    avail_w = cls._avail_media_w(final_w)
                    display_w = min(media_img.width, avail_w)
                    ratio = display_w / media_img.width
                    display_h = int(media_img.height * ratio)
                    media_img = media_img.resize((display_w, display_h), Image.LANCZOS)
                    canvas.alpha_composite(media_img, (cls.X_OFFSET, inner_y))
                    inner_y += display_h + 6
                except Exception:
                    pass

            curr_y += entry_heights[i]

            if i < len(entries) - 1:
                sep_y = curr_y
                draw.line([cls.X_OFFSET, sep_y, final_w - cls.PADDING, sep_y], fill=(50, 55, 60), width=1)
                curr_y += cls.SEP_GAP

        out = io.BytesIO()
        canvas.save(out, format="PNG")
        return out.getvalue(), final_w, total_h


@loader.tds
class QuoteModule(loader.Module):
    strings = {
        "processing": "🎨 <b>Rendering visual quote...</b>",
        "no_reply": "❌ <b>Context required:</b> Reply to a message.",
        "font_err": "❌ <b>Resource error:</b> Typography assets not loaded.",
        "font_render_err": "❌ <b>Engine error:</b> Font rasterization failed.",
        "no_quoteable": "❌ <b>No quoteable messages found.</b>"
    }

    async def _matrix_start(self, mx):
        self._fonts = {}
        try:
            data_path = cutils.get_data_path()
            reg_path = data_path / "Roboto-Regular.ttf"
            bold_path = data_path / "Roboto-Bold.ttf"

            if reg_path.exists():
                self._fonts["regular"] = reg_path.read_bytes()
            else:
                reg_url = "https://github.com/googlefonts/roboto/raw/main/src/hinted/Roboto-Regular.ttf"
                self._fonts["regular"] = await utils.request(reg_url, return_type="bytes")
                reg_path.write_bytes(self._fonts["regular"])

            if bold_path.exists():
                self._fonts["bold"] = bold_path.read_bytes()
            else:
                bold_url = "https://github.com/googlefonts/roboto/raw/main/src/hinted/Roboto-Bold.ttf"
                self._fonts["bold"] = await utils.request(bold_url, return_type="bytes")
                bold_path.write_bytes(self._fonts["bold"])

            self.logger.info("Typography assets successfully buffered in memory.")
        except Exception as e:
            self.logger.error(f"Asset acquisition failed: {e}")

    async def _build_entry(self, mx, evt) -> Optional[QuoteEntry]:
        try:
            sender = evt.sender
            name = (await mx.client.get_displayname(sender)) or sender
            avatar_url = await mx.client.get_avatar_url(sender)
            content = evt.content
            msgtype = content.msgtype
            text = content.body or " "

            nested_event = None
            nested_text = None
            nested_name = None

            rel = getattr(content, "relates_to", None)
            if rel and getattr(rel, "in_reply_to", None):
                try:
                    nested_event = await utils.get_reply_event(mx, evt)
                    if nested_event:
                        nested_name = nested_event.sender
                        nested_msgtype = nested_event.content.msgtype
                        if nested_msgtype == MessageType.VIDEO:
                            nested_text = "(video)"
                        elif nested_msgtype in (MessageType.IMAGE, MessageType.STICKER):
                            nested_text = "(image)"
                        else:
                            nested_text = nested_event.content.body or ""
                except Exception:
                    pass

            av_bytes = None
            if avatar_url:
                try:
                    av_bytes = await utils.download(mx, meta=DownloadMeta(url=avatar_url))
                except:
                    pass

            media_bytes = None
            if msgtype == MessageType.VIDEO:
                media_bytes = await utils.download(mx, meta=DownloadMeta(url=evt, thumbnail=True))
            elif msgtype in (MessageType.IMAGE, MessageType.STICKER):
                media_bytes = await utils.download(mx, meta=DownloadMeta(url=evt, thumbnail=True))
                if not media_bytes:
                    try:
                        d = await utils.download(mx, meta=DownloadMeta(url=evt))
                        media_bytes = d.url if d else None
                    except Exception:
                        pass

            return QuoteEntry(
                sender_name=name,
                text=text,
                avatar_bytes=av_bytes,
                nested_name=nested_name,
                nested_text=nested_text,
                media_bytes=media_bytes,
            )
        except Exception:
            return None

    @loader.command()
    async def q(self, mx, event: MessageEvent):
        """[count] - Create Element-style quote. Reply + q [N] for multi-quote."""
        if not self._fonts.get("regular") or not self._fonts.get("bold"):
            raise UsageError(self.strings["font_err"])

        args = await cutils.get_args(mx, event)
        count = 1
        if args:
            try:
                count = max(1, int(args[0]))
            except ValueError:
                count = 1

        reply = await utils.get_reply_event(mx, event)

        if not reply:
            raise UsageError(self.strings["no_reply"])

        status_id = await utils.answer(mx, self.strings["processing"])

        entries = []

        if count == 1:
            entry = await self._build_entry(mx, reply)
            if entry:
                entries.append(entry)
        else:
            context_events = await utils.get_context_events(
                mx, event.room_id, reply.event_id, limit=50
            )
            context_events.reverse()
            for evt in context_events:
                if len(entries) >= count:
                    break
                if not evt.content.body:
                    continue
                entry = await self._build_entry(mx, evt)
                if entry:
                    entries.append(entry)

        if not entries:
            raise UsageError(self.strings["no_quoteable"])

        result, width, height = await asyncio.to_thread(
            QuoteEngine.render,
            entries,
            self._fonts,
            self.strings
        )

        await utils.answer(
            mx,
            media=MXImage(
                url=result,
                w=width,
                h=height,
                mimetype="image/png"

            ),
            edit_id=status_id
        )

import io
import asyncio
import textwrap
from typing import Dict, Optional, Tuple

from pydantic import BaseModel, ConfigDict
from mautrix.types import MessageEvent, Event
from PIL import Image, ImageDraw, ImageFont, ImageOps

from ..core import loader, utils
from ..core.exceptions import UsageError
from ..core.utils.media_types import Image as MXImage


class Meta:
    name = "Quote"
    description = "Element-style quotes"
    version = "2.2.0"
    tags = ["image", "media"]
    dependencies = ["pillow"]
    author = "@pasha:pashahatsune.pp.ua"


class QuoteEntry(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    sender_name: str
    text: str
    avatar_bytes: Optional[bytes] = None
    nested_name: Optional[str] = None
    nested_text: Optional[str] = None


class QuoteEngine:
    MAX_W, MIN_W, X_OFFSET, PADDING = 600, 200, 75, 18
    SEP_GAP = 8

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
        "invalid_image": "❌ <b>Media error:</b> Failed to process avatar.",
        "no_quoteable": "❌ <b>No quoteable messages found.</b>"
    }

    async def _matrix_start(self, mx):
        self._fonts = {}
        try:
            reg_url = "https://github.com/googlefonts/roboto/raw/main/src/hinted/Roboto-Regular.ttf"
            bold_url = "https://github.com/googlefonts/roboto/raw/main/src/hinted/Roboto-Bold.ttf"

            self._fonts["regular"] = await utils.request(reg_url, return_type="bytes")
            self._fonts["bold"] = await utils.request(bold_url, return_type="bytes")

            self.logger.info("Typography assets successfully buffered in memory.")
        except Exception as e:
            self.logger.error(f"Asset acquisition failed: {e}")

    async def _build_entry(self, mx, evt) -> Optional[QuoteEntry]:
        try:
            sender = evt.sender
            name = (await mx.client.get_displayname(sender)) or sender
            avatar_url = await mx.client.get_avatar_url(sender)
            text = getattr(evt.content, "body", "") or " "

            nested_name = None
            nested_text = None
            nested_event = await utils.get_reply_event(mx, evt)
            if nested_event:
                nested_name = (await mx.client.get_displayname(nested_event.sender)) or "User"
                nested_text = (getattr(nested_event.content, "body", "") or "(media)").replace("\n", " ")

            av_bytes = None
            if avatar_url:
                try:
                    av_bytes = await mx.client.download_media(avatar_url)
                except:
                    pass

            return QuoteEntry(
                sender_name=name,
                text=text,
                avatar_bytes=av_bytes,
                nested_name=nested_name,
                nested_text=nested_text,
            )
        except Exception:
            return None

    @loader.command()
    async def q(self, mx, event: MessageEvent):
        """[count] - Create Element-style quote. Reply + /q [N] for multi-quote."""
        if not self._fonts.get("regular") or not self._fonts.get("bold"):
            raise UsageError(self.strings["font_err"])

        args = await utils.get_args(mx, event)
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
            reply_to = event.content.relates_to.in_reply_to
            context = await mx.client.api.request(
                "GET",
                f"/_matrix/client/v3/rooms/{event.room_id}/context/{reply_to.event_id}",
            )

            before = context.get("events_before", [])
            the_event = context.get("event")
            all_dicts = before + ([the_event] if the_event else [])
            all_dicts = all_dicts[-count:]

            for evt_dict in all_dicts:
                try:
                    evt = Event.deserialize(evt_dict)

                    if evt.type == "m.room.encrypted":
                        from ..core.utils.events import decrypt_event
                        if not await decrypt_event(mx, evt):
                            continue

                    if not getattr(evt.content, "body", None):
                        continue

                    entry = await self._build_entry(mx, evt)
                    if entry:
                        entries.append(entry)
                except Exception:
                    continue

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

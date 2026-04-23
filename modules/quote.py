import io
import asyncio
import textwrap
from typing import Dict, Optional, Tuple

from pydantic import BaseModel, ConfigDict
from mautrix.types import MessageEvent, ImageInfo
from PIL import Image, ImageDraw, ImageFont, ImageOps

from ...core import loader, utils
from ...core.exceptions import UsageError


class Meta:
    name = "Quote"
    description = "Element-style quotes"
    version = "2.1.0"
    tags = ["image", "media"]
    dependencies = ["pillow"]
    author = "@pasha:pashahatsune.pp.ua"


class QuoteData(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    sender_name: str
    text: str
    avatar_bytes: Optional[bytes] = None
    nested_name: Optional[str] = None
    nested_text: Optional[str] = None


class QuoteEngine:
    @staticmethod
    def render(data: QuoteData, fonts: Dict[str, bytes], strings: Dict[str, str]) -> Tuple[bytes, int, int]:
        try:
            f_name = ImageFont.truetype(io.BytesIO(fonts["bold"]), 18)
            f_text = ImageFont.truetype(io.BytesIO(fonts["regular"]), 17)
            f_reply_name = ImageFont.truetype(io.BytesIO(fonts["bold"]), 14)
            f_reply_text = ImageFont.truetype(io.BytesIO(fonts["regular"]), 14)
        except Exception as e:
            raise RuntimeError(strings["font_render_err"]) from e

        MAX_W, MIN_W, X_OFFSET, PADDING = 600, 200, 75, 18
        
        tmp_draw = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
        
        main_lines = []
        for line in data.text.splitlines():
            main_lines.extend(textwrap.wrap(line, width=45))

        name_w = tmp_draw.textbbox((0, 0), data.sender_name, f_name)[2]
        
        max_line_w = 0
        for line in main_lines:
            max_line_w = max(max_line_w, tmp_draw.textbbox((0, 0), line, f_text)[2])
        
        nested_w = 0
        if data.nested_name:
            nw_name = tmp_draw.textbbox((0, 0), data.nested_name, f_reply_name)[2]
            nw_text = tmp_draw.textbbox((0, 0), (data.nested_text or "")[:70], f_reply_text)[2]
            nested_w = max(nw_name, nw_text) + 15

        content_w = max(name_w, max_line_w, nested_w)
        final_w = int(max(MIN_W, min(content_w + X_OFFSET + PADDING, MAX_W)))

        height = PADDING + 24
        if data.nested_name:
            height += 48
        height = int(height + len(main_lines) * 22 + PADDING)

        canvas = Image.new("RGBA", (final_w, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(canvas)
        draw.rounded_rectangle([0, 0, final_w, height], radius=18, fill=(21, 25, 30, 255))

        if data.avatar_bytes:
            try:
                av = Image.open(io.BytesIO(data.avatar_bytes)).convert("RGBA")
                av = ImageOps.fit(av, (48, 48), centering=(0.5, 0.5))
                mask = Image.new("L", (48, 48), 0)
                ImageDraw.Draw(mask).ellipse((0, 0, 48, 48), fill=255)
                av.putalpha(mask)
                canvas.alpha_composite(av, (15, PADDING))
            except:
                draw.ellipse([15, PADDING, 15+48, PADDING+48], fill=(50, 55, 60))
        else:
            draw.ellipse([15, PADDING, 15+48, PADDING+48], fill=(50, 55, 60))

        draw.text((X_OFFSET, PADDING), data.sender_name, font=f_name, fill=(255, 178, 239, 255))
        curr_y = PADDING + 28

        if data.nested_name:
            draw.rectangle([X_OFFSET, curr_y, X_OFFSET + 2, curr_y + 38], fill=(255, 178, 239, 255))
            draw.text((X_OFFSET + 12, curr_y), data.nested_name, font=f_reply_name, fill=(255, 178, 239, 180))
            n_crop = (data.nested_text or "")[:75]
            if len(data.nested_text or "") > 75: n_crop += "..."
            draw.text((X_OFFSET + 12, curr_y + 18), n_crop, font=f_reply_text, fill=(141, 151, 165, 255))
            curr_y += 46

        for line in main_lines:
            draw.text((X_OFFSET, curr_y), line, font=f_text, fill=(225, 225, 225, 255))
            curr_y += 22

        out = io.BytesIO()
        canvas.save(out, format="PNG")
        return out.getvalue(), final_w, height


@loader.tds
class QuoteModule(loader.Module):
    strings = {
        "processing": "🎨 <b>Rendering visual quote...</b>",
        "no_reply": "❌ <b>Context required:</b> Reply to a message.",
        "error": "❌ <b>Render failure:</b> <code>{err}</code>",
        "font_err": "❌ <b>Resource error:</b> Typography assets not loaded.",
        "font_render_err": "❌ <b>Engine error:</b> Font rasterization failed.",
        "invalid_image": "❌ <b>Media error:</b> Failed to process avatar."
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

    @loader.command()
    async def q(self, mx, event: MessageEvent):
        """[reply] - Create Element-style quote"""
        if not self._fonts.get("regular") or not self._fonts.get("bold"):
            raise UsageError(self.strings["font_err"])

        reply = await utils.get_reply_event(mx, event)
        if not reply:
            raise UsageError(self.strings["no_reply"])

        status_id = await utils.answer(mx, self.strings["processing"])

        try:
            sender = reply.sender
            name = (await mx.client.get_displayname(sender)) or sender
            avatar_url = await mx.client.get_avatar_url(sender)
            text = (await utils.get_reply_text(mx, event)) or " "

            nested_data = {}
            nested_event = await utils.get_reply_event(mx, reply)
            if nested_event:
                nested_data["name"] = (await mx.client.get_displayname(nested_event.sender)) or "User"
                body = getattr(nested_event.content, "body", "(media)")
                nested_data["text"] = body.replace("\n", " ")

            av_bytes = None
            if avatar_url:
                try:
                    av_bytes = await mx.client.download_media(avatar_url)
                except:
                    pass

            payload = QuoteData(
                sender_name=name,
                text=text,
                avatar_bytes=av_bytes,
                nested_name=nested_data.get("name"),
                nested_text=nested_data.get("text")
            )

            result, width, height = await asyncio.to_thread(
                QuoteEngine.render,
                payload,
                self._fonts,
                self.strings
            )

            await utils.send_image(
                mx=mx,
                room_id=event.room_id,
                file_bytes=result,
                file_name="quote.png",
                info=ImageInfo(
                    mimetype="image/png", 
                    size=len(result),
                    width=width,
                    height=height
                )
            )
            
            await mx.client.redact(event.room_id, status_id)

        except Exception as e:
            self.logger.error(f"Quote pipeline failed: {e}", exc_info=True)
            err_msg = str(e)
            if err_msg not in self.strings.values():
                err_msg = self.strings["error"].format(err=err_msg)
            await utils.answer(mx, err_msg, edit_id=status_id)
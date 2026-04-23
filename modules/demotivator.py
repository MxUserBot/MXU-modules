import io
import asyncio
import textwrap
from typing import Any, Dict, Optional

from PIL import Image, ImageDraw, ImageFont, ImageOps
from mautrix.types import MessageEvent, MessageType
from pydantic import BaseModel, Field, model_validator, ConfigDict

from ...core import loader, utils
from ...core.exceptions import UsageError


class Meta:
    name = "Demotivator"
    description = "demotivator generator."
    version = "4.1.0"
    tags = ["image", "media"]
    dependencies = ["pillow"]
    author = "@pasha:pashahatsune.pp.ua"


class DemotPayload(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    top: str = Field(min_length=1)
    bottom: str = Field(default="")

    @model_validator(mode='before')
    @classmethod
    def split_payload(cls, v: Any):
        if isinstance(v, str):
            parts = v.split("|", 1)
            return {
                "top": parts[0],
                "bottom": parts[1] if len(parts) > 1 else ""
            }
        return v

class DemotivatorEngine:
    @staticmethod
    def render(
        img_bytes: bytes,
        payload: DemotPayload,
        font_data: bytes,
        strings: Dict[str, str]
    ) -> bytes:
        try:
            source = Image.open(io.BytesIO(img_bytes)).convert("RGBA")
            source = ImageOps.exif_transpose(source)
        except Exception as e:
            raise ValueError(strings["invalid_image"]) from e

        base_width = 800
        w_percent = base_width / float(source.size[0])
        base_height = int(float(source.size[1]) * float(w_percent))
        source = source.resize((base_width, base_height), Image.Resampling.LANCZOS)

        outer_margin, img_padding, border_thickness = 60, 45, 3
        
        try:
            font_top = ImageFont.truetype(io.BytesIO(font_data), 70)
            font_bottom = ImageFont.truetype(io.BytesIO(font_data), 35)
        except Exception as e:
            raise RuntimeError(strings["font_render_err"]) from e

        top_lines = textwrap.wrap(payload.top.upper(), width=25)
        bottom_lines = textwrap.wrap(payload.bottom, width=45)

        text_height = (len(top_lines) * 80) + (len(bottom_lines) * 45) + 60
        canvas_w = base_width + (outer_margin * 2) + (img_padding * 2)
        canvas_h = base_height + (outer_margin * 2) + (img_padding * 2) + text_height
        
        canvas = Image.new("RGB", (canvas_w, canvas_h), (0, 0, 0))
        draw = ImageDraw.Draw(canvas)

        ix, iy = outer_margin + img_padding, outer_margin + img_padding
        f_x0, f_y0 = ix - 8, iy - 8
        f_x1, f_y1 = ix + base_width + 7, iy + base_height + 7
        
        draw.rectangle([f_x0, f_y0, f_x1, f_y1], outline="white", width=border_thickness)
        canvas.paste(source, (ix, iy), source)

        current_y = f_y1 + 45
        for line in top_lines:
            w = draw.textbbox((0, 0), line, font=font_top)[2]
            draw.text(((canvas_w - w) // 2, current_y), line, font=font_top, fill="white")
            current_y += 80

        current_y += 10
        for line in bottom_lines:
            w = draw.textbbox((0, 0), line, font=font_bottom)[2]
            draw.text(((canvas_w - w) // 2, current_y), line, font=font_bottom, fill="white")
            current_y += 45

        out = io.BytesIO()
        canvas.save(out, format="JPEG", quality=95, optimize=True)
        return out.getvalue()


@loader.tds
class DemotivatorModule(loader.Module):
    strings = {
        "processing": "🖼 | <b>Constructing visual asset...</b>",
        "error": "❌ | <b>Deployment failure:</b> <code>{err}</code>",
        "no_reply": "❌ | <b>Context required:</b> Reply to an image.",
        "font_err": "❌ <b>Resource error:</b> Strategic fonts not loaded.",
        "download_err": "❌ | <b>Media error:</b> Failed to download target.",
        "invalid_image": "❌ | <b>Media error:</b> Target must be a valid image.",
        "font_render_err": "❌ | <b>Render error:</b> Font rendering subsystem failed."
    }


    async def _matrix_start(self, mx):
        self._font_data: Optional[bytes] = None
        try:
            url = "https://github.com/googlefonts/roboto/raw/main/src/hinted/Roboto-Regular.ttf"
            self._font_data = await utils.request(url, return_type="bytes")
            if self._font_data:
                self.logger.info("Font data successfully loaded into memory.")
        except Exception as e:
            raise e


    @loader.command()
    async def demot(
        self,
        mx,
        event: MessageEvent,
        text: DemotPayload
    ):
        """<top | bottom> | Generate high-fidelity demotivator using pipe separation"""
        
        if not self._font_data:
            raise UsageError(self.strings["font_err"])

        reply_id = event.content.get_reply_to()


        status_id = await utils.answer(mx, self.strings["processing"])

        try:
            target = await mx.client.get_event(event.room_id, reply_id)
            if target.content.msgtype != MessageType.IMAGE:
                raise ValueError(self.strings["invalid_image"])

            img_bytes = await mx.client.download_media(target.content.url)
            if not img_bytes:
                raise ValueError(self.strings["download_err"])

            result = await asyncio.to_thread(
                DemotivatorEngine.render,
                img_bytes, 
                text, 
                self._font_data,
                self.strings
            )

            await utils.send_image(mx, event.room_id, file_bytes=result, file_name="demot.jpg")
            await mx.client.redact(event.room_id, status_id)

        except Exception as e:
            self.logger.error(f"Pipeline error: {e}", exc_info=True)
            
            err_msg = str(e)
            if err_msg not in self.strings.values():
                err_msg = self.strings["error"].format(err=err_msg)
            
            await utils.answer(mx, err_msg, edit_id=status_id)
            raise RuntimeError(err_msg) from e
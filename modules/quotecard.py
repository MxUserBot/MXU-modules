import io
import asyncio
import textwrap

from PIL import Image, ImageDraw, ImageFont
from mautrix.types import MessageEvent, EventType

from ...core import loader, utils
from ...core.types import Image as Mimage
from ...core.exceptions import UsageError


class Meta:
    name = "Quotes"
    description = "rendering card-quote style images."
    version = "3.6.0" 
    tags = ["image", "media"]
    dependencies = ["pillow"]
    author = "@pasha:pashahatsune.pp.ua"


@loader.tds
class QuotesModule(loader.Module):
    strings = {
        "processing": "🎨 | <b>create image..</b>",
        "error": "❌ | <b>Engine failure:</b> <code>{err}</code>",
        "no_reply": "❌ | <b>Context required:</b> Reply to a message.",
        "no_text": "❌ | <b>Payload missing:</b> No content to render."
    }

    config = {
        "bg_darkness": loader.ConfigValue(
            default=160,
            description="Background darkness (0-255)"
        ),
        "text_box_alpha": loader.ConfigValue(
            default=110,
            description="Transparency of the box (0-255)"
        )
    }


    async def _matrix_start(self, mx):
        self._font_bytes = None
        try:
            url = "https://github.com/googlefonts/roboto/raw/main/src/hinted/Roboto-Medium.ttf"
            self._font_bytes = await utils.request(url, return_type="bytes")
        except Exception as e:
            self.logger.error(f"Strategic asset fetch failed: {e}")


    def _generate_payload(
        self,
        avatar_bytes,
        text,
        author
    ) -> bytes:
        canvas_size = (1200, 600)
        
        try:
            source_img = Image.open(io.BytesIO(avatar_bytes)).convert("RGBA")
            bg = source_img.copy()
            ratio = max(canvas_size[0] / bg.width, canvas_size[1] / bg.height)
            bg = bg.resize((int(bg.width * ratio), int(bg.height * ratio)), Image.Resampling.LANCZOS)
            bg = bg.crop((
                (bg.width - canvas_size[0]) / 2,
                (bg.height - canvas_size[1]) / 2,
                (bg.width + canvas_size[0]) / 2,
                (bg.height + canvas_size[1]) / 2
            ))
        except Exception:
            bg = Image.new("RGBA", canvas_size, (20, 20, 25, 255))

        canvas = Image.alpha_composite(bg, Image.new("RGBA", canvas_size, (0, 0, 0, self.config["bg_darkness"])))

        length = len(text)
        if length < 100:
            f_size, w_width, max_l = 48, 22, 5
        elif length < 300:
            f_size, w_width, max_l = 36, 28, 8
        else:
            f_size, w_width, max_l = 26, 36, 10

        try:
            f_text = ImageFont.truetype(io.BytesIO(self._font_bytes), f_size)
            f_author = ImageFont.truetype(io.BytesIO(self._font_bytes), 32)
        except Exception:
            f_text = f_author = ImageFont.load_default()

        lines = textwrap.wrap(text, width=w_width)
        if len(lines) > max_l:
            lines = lines[:max_l]
            lines[-1] += "..."

        line_spacing = 10
        padding_v = 30  
        padding_h = 50
        gap = 25        
        author_h = 35   
        
        text_h = len(lines) * (f_size + line_spacing)
        box_h = text_h + (padding_v * 2)
        total_group_h = box_h + gap + author_h
        
        group_y_start = (canvas_size[1] - total_group_h) // 2
        group_y_start = max(30, min(group_y_start, 570 - total_group_h))
        
        dummy_draw = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
        max_w = max([dummy_draw.textbbox((0, 0), l, font=f_text)[2] for l in lines])
        author_w = dummy_draw.textbbox((0, 0), f"— {author}", font=f_author)[2]
        box_w = max(max_w, author_w) + (padding_h * 2)
        
        box_x0 = 530
        box_y0 = group_y_start
        box_x1 = min(box_x0 + box_w, 1160)
        box_y1 = box_y0 + box_h
        
        overlay = Image.new("RGBA", canvas_size, (0, 0, 0, 0))
        ImageDraw.Draw(overlay).rounded_rectangle(
            [box_x0, box_y0, box_x1, box_y1],
            radius=30,
            fill=(40, 40, 45, self.config["text_box_alpha"])
        )
        canvas = Image.alpha_composite(canvas, overlay)

        try:
            av = source_img.resize((400, 400), Image.Resampling.LANCZOS)
            mask = Image.new("L", (400, 400), 0)
            ImageDraw.Draw(mask).ellipse((0, 0, 400, 400), fill=255)
            canvas.paste(av, (50, 100), mask)
        except Exception: pass

        draw = ImageDraw.Draw(canvas)
        curr_y = box_y0 + padding_v
        for line in lines:
            draw.text((box_x0 + padding_h, curr_y), line, font=f_text, fill=(255, 255, 255, 255))
            curr_y += (f_size + line_spacing)
            
        draw.text((box_x0 + 40, box_y1 + gap), f"— {author}", font=f_author, fill=(255, 120, 180, 255))

        out = io.BytesIO()
        canvas.save(out, format="PNG")
        return out.getvalue()


    @loader.command()
    async def qcard(
        self,
        mx,
        event: MessageEvent,
        text: str = None
    ) -> None:
        """[text/reply] - Secure aesthetic quote engine"""

        status_id = await utils.answer(mx, self.strings["processing"])

        try:
            target = await utils.get_reply_event(mx, event)

            raw_payload = text or target.content.body
            payload = utils.normalize_text(raw_payload)


            try:
                profile = await mx.client.get_state_event(
                    event.room_id, EventType.ROOM_MEMBER, target.sender
                )
                raw_name = profile.displayname or target.sender
                av_mxc = profile.avatar_url
            except Exception:
                raw_name = target.sender
                av_mxc = None

            name = utils.normalize_text(raw_name)

            av_img = None
            if av_mxc:
                try:
                    av_img = await mx.client.download_media(av_mxc)
                except Exception:
                    pass
                
            result = await asyncio.to_thread(
                self._generate_payload,
                av_img,
                payload,
                name
            )

            await utils.answer(
                mx, 
                edit_id=status_id,
                image=Mimage(
                    url=result, 
                    w=1200, 
                    h=600, 
                    mimetype="image/png"
                )
            )

        except Exception as e:
            raise e

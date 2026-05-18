#			__  ____  ___   _               _           _   
#			|  \/  \ \/ / | | |___  ___ _ __| |__   ___ | |_ 
#			| |\/| |\  /| | | / __|/ _ \ '__| '_ \ / _ \| __|
#			| |  | |/  \| |_| \__ \  __/ |  | |_) | (_) | |_ 
#			|_|  |_/_/\_\\___/|___/\___|_|  |_.__/ \___/ \__| 
#
# 🔒      Licensed under the GNU AGPLv3
# 🌐 https://www.gnu.org/licenses/agpl-3.0.html


class Meta:
    name = "QuotifyPlus"
    description = "Advanced Quote generator with 4 layouts, glass effects, and fake quotes."
    version = "6.0.0" 
    tags = ["image", "media", "formatter"]
    dependencies = ["pillow", "pilmoji", "beautifulsoup4", "markdown", "cairosvg"]
    author = "https://github.com/PashaHatsune"


import io
import asyncio
import re
import base64
import random
import markdown
from bs4 import BeautifulSoup

from PIL import Image, ImageDraw, ImageFont, ImageFilter
from mautrix.types import MessageEvent

from pilmoji import Pilmoji
from pilmoji.source import AppleEmojiSource

from mxc import utils as mxc_utils
from mxc.types import DownloadMeta, Image as Mimage
from mxc.exceptions import UsageError
from .. import loader
from ..core import utils as core_utils


@loader.tds
class QuotifyPlusModule(loader.Module):
    strings = {
        "processing": "🎨 | <b>Generating quote..</b>",
        "error": "❌ | <b>Engine failure:</b> <code>{err}</code>",
        "no_reply": "❌ | <b>Context required:</b> Reply to a message or provide text.",
        "no_text": "❌ | <b>Payload missing:</b> No text to render."
    }

    config = {
        "layout_style": loader.ConfigValue(
            default=0,
            description="Layout: 0=Left, 1=Right, 2=Vertical, 3=Cloud (iOS)"
        ),
        "bg_style": loader.ConfigValue(
            default=1,
            description="Background: 0=Solid, 1=Blur, 2=Glass, 3=Gradient"
        ),
        "bg_dimming": loader.ConfigValue(
            default=80,
            description="Background dimming (0-255)"
        ),
        "text_box_alpha": loader.ConfigValue(
            default=130,
            description="Backdrop opacity (0-255). For Cloud style this is bubble opacity."
        ),
        "cloud_color": loader.ConfigValue(
            default="#1E1E1E",
            description="Cloud style bubble color (HEX)"
        ),
        "text_color": loader.ConfigValue(
            default="#FFFFFF",
            description="Main text color (HEX)"
        ),
        "author_color": loader.ConfigValue(
            default="#B4B4B4",
            description="Author name color (HEX)"
        )
    }

    async def _matrix_start(self, mx):
        self.font_paths = {}
        fonts_to_download = {
            "regular": "Roboto-Medium.ttf",
            "bold": "Roboto-Bold.ttf",
            "italic": "Roboto-Italic.ttf",
            "bold_italic": "Roboto-BoldItalic.ttf",
            "code": "RobotoMono-Regular.ttf"
        }
        
        for key, filename in fonts_to_download.items():
            path = core_utils.get_data_path() / filename
            if not path.exists():
                try:
                    url = f"https://github.com/googlefonts/roboto/raw/main/src/hinted/{filename}"
                    data = await mxc_utils.request(url, return_type="bytes")
                    path.write_bytes(data)
                except Exception as e:
                    self.logger.error(f"Asset fetch failed for {filename}: {e}")
            
            if path.exists():
                self.font_paths[key] = str(path)

    def _hex_to_rgba(self, hex_color, alpha=255):
        hex_color = hex_color.lstrip('#')
        try:
            return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4)) + (alpha,)
        except:
            return (255, 255, 255, alpha)

    def _clean_matrix_html(self, html_text: str) -> str:
        cleaned = re.sub(r'<mx-reply>.*?</mx-reply>', '', html_text, flags=re.DOTALL)
        return cleaned.strip()

    def _generate_payload(
        self,
        avatar_bytes,
        html_text,
        author,
        is_fake=False
    ) -> bytes:
        canvas_size = (1200, 600)
        layout_style = self.config["layout_style"]
        bg_style = self.config["bg_style"]
        
        avatar_img = None
        if avatar_bytes and not is_fake:
            raw_data = avatar_bytes
            if hasattr(raw_data, "data") and raw_data.data: raw_data = raw_data.data
            elif hasattr(raw_data, "content") and raw_data.content: raw_data = raw_data.content
            if isinstance(raw_data, (bytes, bytearray)):
                try: avatar_img = Image.open(io.BytesIO(raw_data)).convert("RGBA")
                except: pass

        if bg_style == 3:
            bg = Image.new("RGBA", canvas_size)
            draw = ImageDraw.Draw(bg)
            c1 = (random.randint(50, 150), random.randint(20, 80), random.randint(100, 200))
            c2 = (random.randint(10, 40), random.randint(10, 40), random.randint(20, 60))
            for i in range(canvas_size[0]):
                r = int(c1[0] * (1 - i/canvas_size[0]) + c2[0] * (i/canvas_size[0]))
                g = int(c1[1] * (1 - i/canvas_size[0]) + c2[1] * (i/canvas_size[0]))
                b = int(c1[2] * (1 - i/canvas_size[0]) + c2[2] * (i/canvas_size[0]))
                draw.line([(i, 0), (i, canvas_size[1])], fill=(r, g, b, 255))
        else:
            if avatar_img:
                bg_base = Image.new("RGBA", avatar_img.size, (20, 20, 25, 255))
                bg_base = Image.alpha_composite(bg_base, avatar_img)
                bg = bg_base.convert("RGB")
                ratio = max(canvas_size[0] / bg.width, canvas_size[1] / bg.height)
                bg = bg.resize((int(bg.width * ratio), int(bg.height * ratio)), Image.Resampling.LANCZOS)
                crop_x = (bg.width - canvas_size[0]) // 2
                crop_y = (bg.height - canvas_size[1]) // 2
                bg = bg.crop((crop_x, crop_y, crop_x + canvas_size[0], crop_y + canvas_size[1])).convert("RGBA")
                
                if bg_style == 1:
                    bg = bg.filter(ImageFilter.GaussianBlur(12))
                elif bg_style == 2:
                    bg = bg.filter(ImageFilter.GaussianBlur(25))
            else:
                bg = Image.new("RGBA", canvas_size, (30, 30, 35, 255))

        dark_layer = Image.new("RGBA", canvas_size, (0, 0, 0, self.config["bg_dimming"]))
        canvas = Image.alpha_composite(bg, dark_layer)

        avatar_size = 250 if layout_style != 3 else 90
        padding = 40
        gap = 20
        line_spacing = 10
        max_text_width = 750 if layout_style != 3 else 800

        soup = BeautifulSoup(html_text, "html.parser")
        words = []
        
        for element in soup.descendants:
            if element.name in ['br', 'p', 'div']:
                words.append(("\n", {}))
            elif isinstance(element, str):
                text_content = str(element)
                if not any(p.name in ['pre', 'code'] for p in element.parents):
                    text_content = text_content.replace('\n', ' ')
                    text_content = re.sub(r' +', ' ', text_content)
                if not text_content: continue
                
                style = {
                    "bold": any(p.name in ['b', 'strong'] for p in element.parents),
                    "italic": any(p.name in ['i', 'em'] for p in element.parents),
                    "code": any(p.name in ['code', 'pre'] for p in element.parents),
                    "strike": any(p.name in ['s', 'strike', 'del'] for p in element.parents)
                }
                
                parts = re.split(r'( )', text_content)
                current_word = ""
                for p in parts:
                    if p == ' ':
                        words.append((current_word + ' ', style))
                        current_word = ""
                    else:
                        current_word += p
                if current_word: words.append((current_word, style))

        total_chars = sum(len(t) for t, _ in words if t != "\n")
        
        if total_chars < 80: f_size, max_lines = 48, 6
        elif total_chars < 200: f_size, max_lines = 38, 8
        elif total_chars < 400: f_size, max_lines = 28, 11
        else: f_size, max_lines = 24, 14

        def get_font(style):
            try:
                if style.get("code") and self.font_paths.get("code"): return ImageFont.truetype(self.font_paths["code"], f_size)
                if style.get("bold") and style.get("italic") and self.font_paths.get("bold_italic"): return ImageFont.truetype(self.font_paths["bold_italic"], f_size)
                if style.get("bold") and self.font_paths.get("bold"): return ImageFont.truetype(self.font_paths["bold"], f_size)
                if style.get("italic") and self.font_paths.get("italic"): return ImageFont.truetype(self.font_paths["italic"], f_size)
                if self.font_paths.get("regular"): return ImageFont.truetype(self.font_paths["regular"], f_size)
            except Exception: pass
            return ImageFont.load_default()

        f_author = ImageFont.truetype(self.font_paths.get("regular"), max(24, int(f_size * 0.8)))

        dummy_img = Image.new("RGBA", (1, 1))
        dummy_draw = ImageDraw.Draw(dummy_img)

        lines = []
        current_line = []
        current_width = 0

        with Pilmoji(dummy_img, source=AppleEmojiSource) as p_dummy:
            def get_w(t, f):
                try: return p_dummy.getsize(t, font=f)[0]
                except AttributeError: return dummy_draw.textlength(t, font=f)

            for word_text, style in words:
                if word_text == "\n":
                    lines.append(current_line)
                    current_line = []
                    current_width = 0
                    continue
                    
                font = get_font(style)
                w = get_w(word_text, font)
                
                if w > max_text_width and word_text.strip():
                    for char in word_text:
                        cw = get_w(char, font)
                        if current_width + cw > max_text_width:
                            lines.append(current_line)
                            current_line = []
                            current_width = 0
                        current_line.append((char, font, style, cw))
                        current_width += cw
                    continue

                if current_width + w > max_text_width and word_text.strip():
                    if current_line:
                        lines.append(current_line)
                        current_line = []
                        current_width = 0
                
                if current_width == 0 and not word_text.strip(): continue
                current_line.append((word_text, font, style, w))
                current_width += w
                
            if current_line: lines.append(current_line)
            while lines and not any(part.strip() for part, _, _, _ in lines[0]): lines.pop(0)
            while lines and not any(part.strip() for part, _, _, _ in lines[-1]): lines.pop(-1)

            if len(lines) > max_lines:
                lines = lines[:max_lines]
                font_ellipsis = get_font({"bold": False, "italic": False, "code": False, "strike": False})
                lines[-1].append(("...", font_ellipsis, {"strike": False}, get_w("...", font_ellipsis)))

            max_line_width = max([sum(w for _, _, _, w in line) for line in lines] + [0])
            author_prefix = "" if layout_style == 3 else "— "
            author_text = f"{author_prefix}{author}"
            author_w = get_w(author_text, f_author)

        text_color = self._hex_to_rgba(self.config["text_color"], 255)
        author_color = self._hex_to_rgba(self.config["author_color"], 255)
        
        text_block_height = len(lines) * (f_size + line_spacing)
        total_text_height = text_block_height + gap + f_size
        
        rendered_avatar = None
        if avatar_img and not is_fake:
            try:
                min_side = min(avatar_img.width, avatar_img.height)
                cx, cy = (avatar_img.width - min_side)//2, (avatar_img.height - min_side)//2
                crop = avatar_img.crop((cx, cy, cx + min_side, cy + min_side))
                rendered_avatar = crop.resize((avatar_size, avatar_size), Image.Resampling.LANCZOS)
            except: pass

        if not rendered_avatar:
            rendered_avatar = Image.new("RGBA", (avatar_size, avatar_size), (0, 0, 0, 0))
            cdraw = ImageDraw.Draw(rendered_avatar)
            c_color = tuple(random.randint(80, 200) for _ in range(3)) + (255,)
            cdraw.ellipse((0, 0, avatar_size, avatar_size), fill=c_color)
            letter = author.strip()[0].upper() if author.strip() else "?"
            try: lf = ImageFont.truetype(self.font_paths.get("bold", self.font_paths.get("regular")), int(avatar_size * 0.45))
            except: lf = ImageFont.load_default()
            
            try:
                bbox = cdraw.textbbox((0, 0), letter, font=lf)
                w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
                ox, oy = bbox[0], bbox[1]
            except:
                w, h, ox, oy = cdraw.textlength(letter, font=lf), int(avatar_size*0.45), 0, 0
            cdraw.text(((avatar_size - w) // 2 - ox, (avatar_size - h) // 2 - oy), letter, font=lf, fill=(255, 255, 255))

        mask = Image.new("L", (avatar_size, avatar_size), 0)
        ImageDraw.Draw(mask).ellipse((0, 0, avatar_size, avatar_size), fill=255)
        rendered_avatar.putalpha(mask)

        overlay = Image.new("RGBA", canvas_size, (0, 0, 0, 0))
        draw_ov = ImageDraw.Draw(overlay)
        
        if layout_style == 3:
            bubble_pad = 35
            box_h = total_text_height + bubble_pad * 2
            box_w = max(max_line_width, author_w) + bubble_pad * 2
            
            content_total_w = avatar_size + 15 + box_w
            start_x = (canvas_size[0] - content_total_w) // 2
            start_y = (canvas_size[1] - box_h) // 2

            ava_x = start_x
            ava_y = start_y + box_h - avatar_size
            canvas.paste(rendered_avatar, (ava_x, ava_y), rendered_avatar)
            
            bubble_x = ava_x + avatar_size + 15
            bubble_color = self._hex_to_rgba(self.config["cloud_color"], self.config["text_box_alpha"])

            tail_coords = [(bubble_x, start_y + box_h - 20), (bubble_x - 12, start_y + box_h), (bubble_x + 25, start_y + box_h)]
            draw_ov.polygon(tail_coords, fill=bubble_color)
            draw_ov.rounded_rectangle([bubble_x, start_y, bubble_x + box_w, start_y + box_h], radius=30, fill=bubble_color)
            
            text_x = bubble_x + bubble_pad
            curr_y = start_y + bubble_pad

            with Pilmoji(overlay, source=AppleEmojiSource) as pilmoji:
                pilmoji.text((text_x, curr_y), author_text, font=f_author, fill=author_color)
                curr_y += f_size + 10
                
                for line in lines:
                    curr_x = text_x
                    grouped_line = []
                    for part, font, style, w in line:
                        if not grouped_line: grouped_line.append([part, font, style, w])
                        else:
                            if grouped_line[-1][2] == style and grouped_line[-1][1] == font:
                                grouped_line[-1][0] += part
                                grouped_line[-1][3] += w
                            else: grouped_line.append([part, font, style, w])
                    
                    for part, font, style, w in grouped_line:
                        if part.strip() or part == ' ':
                            if style.get("code") and part.strip():
                                draw_ov.rounded_rectangle([curr_x - 2, curr_y - 2, curr_x + w + 2, curr_y + f_size + 4], radius=4, fill=(50, 50, 55, 255))
                            pilmoji.text((curr_x, curr_y), part, font=font, fill=text_color)
                            if style.get("strike") and part.strip():
                                draw_ov.line([(curr_x, curr_y + f_size//2 + 2), (curr_x + w, curr_y + f_size//2 + 2)], fill=text_color, width=2)
                        curr_x += w
                    curr_y += f_size + line_spacing

        elif layout_style == 2:
            box_h = avatar_size + padding + total_text_height + padding * 2
            box_w = max(avatar_size, max_line_width, author_w) + padding * 2
            
            box_x0 = (canvas_size[0] - box_w) // 2
            box_y0 = (canvas_size[1] - box_h) // 2
            
            draw_ov.rounded_rectangle([box_x0, box_y0, box_x0 + box_w, box_y0 + box_h], radius=35, fill=(30, 30, 35, self.config["text_box_alpha"]))
            
            ava_x = box_x0 + (box_w - avatar_size) // 2
            ava_y = box_y0 + padding
            canvas.paste(rendered_avatar, (ava_x, ava_y), rendered_avatar)
            
            curr_y = ava_y + avatar_size + padding
            
            with Pilmoji(overlay, source=AppleEmojiSource) as pilmoji:
                for line in lines:
                    line_w = sum(w for _, _, _, w in line)
                    curr_x = box_x0 + (box_w - line_w) // 2
                    
                    grouped_line = []
                    for part, font, style, w in line:
                        if not grouped_line: grouped_line.append([part, font, style, w])
                        else:
                            if grouped_line[-1][2] == style and grouped_line[-1][1] == font:
                                grouped_line[-1][0] += part
                                grouped_line[-1][3] += w
                            else: grouped_line.append([part, font, style, w])
                            
                    for part, font, style, w in grouped_line:
                        if part.strip() or part == ' ':
                            if style.get("code") and part.strip():
                                draw_ov.rounded_rectangle([curr_x - 2, curr_y - 2, curr_x + w + 2, curr_y + f_size + 4], radius=4, fill=(50, 50, 55, 255))
                            pilmoji.text((curr_x, curr_y), part, font=font, fill=text_color)
                            if style.get("strike") and part.strip():
                                draw_ov.line([(curr_x, curr_y + f_size//2 + 2), (curr_x + w, curr_y + f_size//2 + 2)], fill=text_color, width=2)
                        curr_x += w
                    curr_y += f_size + line_spacing
                
                curr_y += gap
                auth_x = box_x0 + (box_w - author_w) // 2
                pilmoji.text((auth_x, curr_y), author_text, font=f_author, fill=author_color)

        else:
            box_h = max(avatar_size, total_text_height) + padding * 2
            box_w = padding + avatar_size + padding + max(max_line_width, author_w) + padding
            
            box_x0 = (canvas_size[0] - box_w) // 2
            box_y0 = (canvas_size[1] - box_h) // 2
            
            draw_ov.rounded_rectangle([box_x0, box_y0, box_x0 + box_w, box_y0 + box_h], radius=35, fill=(30, 30, 35, self.config["text_box_alpha"]))
            
            if layout_style == 0:
                ava_x = box_x0 + padding
                text_x = ava_x + avatar_size + padding
            else:
                ava_x = box_x0 + box_w - padding - avatar_size
                text_x = box_x0 + padding
                
            ava_y = box_y0 + (box_h - avatar_size) // 2
            canvas.paste(rendered_avatar, (ava_x, ava_y), rendered_avatar)

            curr_y = box_y0 + (box_h - total_text_height) // 2

            with Pilmoji(overlay, source=AppleEmojiSource) as pilmoji:
                for line in lines:
                    line_w = sum(w for _, _, _, w in line)
                    curr_x = text_x
                    if layout_style == 1:
                        curr_x = ava_x - padding - line_w
                        
                    grouped_line = []
                    for part, font, style, w in line:
                        if not grouped_line: grouped_line.append([part, font, style, w])
                        else:
                            if grouped_line[-1][2] == style and grouped_line[-1][1] == font:
                                grouped_line[-1][0] += part
                                grouped_line[-1][3] += w
                            else: grouped_line.append([part, font, style, w])
                            
                    for part, font, style, w in grouped_line:
                        if part.strip() or part == ' ':
                            if style.get("code") and part.strip():
                                draw_ov.rounded_rectangle([curr_x - 2, curr_y - 2, curr_x + w + 2, curr_y + f_size + 4], radius=4, fill=(50, 50, 55, 255))
                            pilmoji.text((curr_x, curr_y), part, font=font, fill=text_color)
                            if style.get("strike") and part.strip():
                                draw_ov.line([(curr_x, curr_y + f_size//2 + 2), (curr_x + w, curr_y + f_size//2 + 2)], fill=text_color, width=2)
                        curr_x += w
                    curr_y += f_size + line_spacing
                
                curr_y += gap
                auth_x = text_x
                if layout_style == 1:
                    auth_x = ava_x - padding - author_w
                pilmoji.text((auth_x, curr_y), author_text, font=f_author, fill=author_color)

        canvas = Image.alpha_composite(canvas, overlay)
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
        """[text / separator | text] - Generate a quote card. Use "|" as separator for fake quotes."""

        status_id = await mxc_utils.answer(mx, self.strings["processing"])

        try:
            target = await mxc_utils.get_reply_event(mx, event)
            if not target and not text:
                raise UsageError(self.strings["no_reply"])

            raw_text = text or ""
            is_fake = False
            author_override = None
            avatar_override = None
            
            if "|" in raw_text:
                if target:
                    parts = raw_text.split("|", 1)
                    raw_text = parts[0].strip()
                    if len(parts) > 1:
                        avatar_override = parts[1].strip()
                else:
                    parts = raw_text.split("|", 2)
                    author_override = parts[0].strip()
                    raw_text = parts[1].strip()
                    is_fake = True
                    if len(parts) > 2:
                        avatar_override = parts[2].strip()

            html_payload = ""
            if not is_fake and target and not raw_text:
                if hasattr(target.content, "formatted_body") and target.content.formatted_body:
                    html_payload = self._clean_matrix_html(target.content.formatted_body)
                else:
                    cleaned_body = core_utils.normalize_text(target.content.body or "", keep_alnum=True)
                    html_payload = markdown.markdown(cleaned_body, extensions=['nl2br'])
            else:
                if not raw_text and target:
                    raw_text = target.content.body
                cleaned_text = core_utils.normalize_text(raw_text, keep_alnum=True)
                html_payload = markdown.markdown(cleaned_text, extensions=['nl2br'])

            sender = target.sender if target and not is_fake else event.sender
            
            if author_override:
                name = core_utils.normalize_text(author_override, keep_alnum=True)
                av_img = None
            else:
                profile = await mxc_utils.get_profile(mx, sender)
                raw_name = profile.displayname
                name = core_utils.normalize_text(raw_name, keep_alnum=True)
                av_img = None
                if profile.avatar_url:
                    try:
                        av_img = await mxc_utils.download(mx, meta=DownloadMeta(url=profile.avatar_url))
                    except: pass

            if avatar_override and avatar_override.startswith("mxc://"):
                try:
                    av_img = await mxc_utils.download(mx, meta=DownloadMeta(url=avatar_override))
                except:
                    pass

            result = await asyncio.to_thread(
                self._generate_payload,
                av_img,
                html_payload,
                name,
                is_fake
            )

            await mxc_utils.answer(
                mx, 
                edit_id=status_id,
                media=Mimage(
                    url=result, 
                    w=1200, 
                    h=600, 
                    mimetype="image/png"
                )
            )

        except UsageError:
            raise
        except Exception as e:
            raise e
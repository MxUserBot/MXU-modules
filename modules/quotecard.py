#			__  ____  ___   _               _           _   
#			|  \/  \ \/ / | | |___  ___ _ __| |__   ___ | |_ 
#			| |\/| |\  /| | | / __|/ _ \ '__| '_ \ / _ \| __|
#			| |  | |/  \| |_| \__ \  __/ |  | |_) | (_) | |_ 
#			|_|  |_/_/\_\\___/|___/\___|_|  |_.__/ \___/ \__| 
#
# 🔒      Licensed under the GNU AGPLv3
# 🌐 https://www.gnu.org/licenses/agpl-3.0.html


class Meta:
    name = "Quotes"
    description = "Premium Matrix quotes with blurred background and pixel-perfect Apple emojis."
    version = "5.2.0" 
    tags = ["image", "media", "formatter"]
    dependencies = ["pillow", "pilmoji", "beautifulsoup4", "markdown"]
    author = "https://github.com/PashaHatsune"


import io
import asyncio
import re
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
from .. import loader, utils as core_utils


@loader.tds
class QuotesModule(loader.Module):
    strings = {
        "processing": "🎨 | <b>Создаю цитату..</b>",
        "error": "❌ | <b>Engine failure:</b> <code>{err}</code>",
        "no_reply": "❌ | <b>Context required:</b> Ответьте на сообщение.",
        "no_text": "❌ | <b>Payload missing:</b> Нет текста для рендера."
    }

    config = {
        "bg_darkness": loader.ConfigValue(
            default=160,
            description="Насколько сильно затемнять фон-аватарку (0-255)"
        ),
        "text_box_alpha": loader.ConfigValue(
            default=130,
            description="Непрозрачность центральной плашки с текстом (0-255)"
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

    def _clean_matrix_html(self, html_text: str) -> str:
        cleaned = re.sub(r'<mx-reply>.*?</mx-reply>', '', html_text, flags=re.DOTALL)
        return cleaned.strip()

    def _generate_payload(
        self,
        avatar_bytes,
        html_text,
        author
    ) -> bytes:
        canvas_size = (1200, 600)
        
        # 1. Извлекаем реальные байты из mxc-объекта
        avatar_img = None
        raw_data = avatar_bytes
        if raw_data is not None:
            if hasattr(raw_data, "data") and raw_data.data:
                raw_data = raw_data.data
            elif hasattr(raw_data, "content") and raw_data.content:
                raw_data = raw_data.content
                
            if isinstance(raw_data, (bytes, bytearray)):
                try:
                    avatar_img = Image.open(io.BytesIO(raw_data)).convert("RGBA")
                except Exception:
                    pass

        # 2. Создание размытого фона из аватарки
        if avatar_img:
            try:
                # Накладываем на темный фон, чтобы прозрачные PNG не чернели
                bg_base = Image.new("RGBA", avatar_img.size, (20, 20, 25, 255))
                bg_base = Image.alpha_composite(bg_base, avatar_img)
                bg = bg_base.convert("RGB")
                
                ratio = max(canvas_size[0] / bg.width, canvas_size[1] / bg.height)
                bg = bg.resize((int(bg.width * ratio), int(bg.height * ratio)), Image.Resampling.LANCZOS)
                
                crop_x = (bg.width - canvas_size[0]) // 2
                crop_y = (bg.height - canvas_size[1]) // 2
                bg = bg.crop((crop_x, crop_y, crop_x + canvas_size[0], crop_y + canvas_size[1]))
                
                # Сильный блюр для премиального эффекта
                bg = bg.filter(ImageFilter.GaussianBlur(10)).convert("RGBA")
            except Exception:
                bg = Image.new("RGBA", canvas_size, (20, 20, 25, 255))
        else:
            bg = Image.new("RGBA", canvas_size, (20, 20, 25, 255))

        # Затемняем фон
        dark_layer = Image.new("RGBA", canvas_size, (0, 0, 0, self.config["bg_darkness"]))
        canvas = Image.alpha_composite(bg, dark_layer)

        # 3. Настройки коробки
        avatar_size = 250
        padding = 40
        gap = 20
        line_spacing = 10
        max_text_width = 750  

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
                
                if not text_content: 
                    continue
                
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
                if current_word:
                    words.append((current_word, style))

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
                
                if current_width == 0 and not word_text.strip():
                    continue
                    
                current_line.append((word_text, font, style, w))
                current_width += w
                
            if current_line:
                lines.append(current_line)

            while lines and not any(part.strip() for part, _, _, _ in lines[0]): lines.pop(0)
            while lines and not any(part.strip() for part, _, _, _ in lines[-1]): lines.pop(-1)

            if len(lines) > max_lines:
                lines = lines[:max_lines]
                font_ellipsis = get_font({"bold": False, "italic": False, "code": False, "strike": False})
                w_ellipsis = get_w("...", font_ellipsis)
                lines[-1].append(("...", font_ellipsis, {"strike": False}, w_ellipsis))

            max_line_width = max([sum(w for _, _, _, w in line) for line in lines] + [0])
            
            author_text = f"— {author}"
            author_w = get_w(author_text, f_author)

        # Расчет плашки
        text_block_height = len(lines) * (f_size + line_spacing)
        total_text_height = text_block_height + gap + f_size
        
        box_h = max(avatar_size, total_text_height) + padding * 2
        box_w = padding + avatar_size + padding + max(max_line_width, author_w) + padding
        
        box_x0 = max(20, (canvas_size[0] - box_w) // 2)
        box_y0 = max(20, (canvas_size[1] - box_h) // 2)

        overlay = Image.new("RGBA", canvas_size, (0, 0, 0, 0))
        ImageDraw.Draw(overlay).rounded_rectangle(
            [box_x0, box_y0, box_x0 + box_w, box_y0 + box_h],
            radius=35,
            fill=(30, 30, 35, self.config["text_box_alpha"])
        )
        canvas = Image.alpha_composite(canvas, overlay)

        # 4. Кружок Аватарки
        avatar_y = box_y0 + (box_h - avatar_size) // 2
        avatar_pos = (box_x0 + padding, avatar_y)

        if avatar_img:
            try:
                min_side = min(avatar_img.width, avatar_img.height)
                crop_x = (avatar_img.width - min_side) // 2
                crop_y = (avatar_img.height - min_side) // 2
                cropped_img = avatar_img.crop((crop_x, crop_y, crop_x + min_side, crop_y + min_side))
                
                img = cropped_img.resize((avatar_size, avatar_size), Image.Resampling.LANCZOS)
                mask = Image.new("L", (avatar_size, avatar_size), 0)
                ImageDraw.Draw(mask).ellipse((0, 0, avatar_size, avatar_size), fill=255)
                img.putalpha(mask)
                canvas.paste(img, avatar_pos, img)
            except Exception:
                pass

        if not avatar_img:
            # Генерация заглушки, если нет авы
            img = Image.new("RGBA", (avatar_size, avatar_size), (0, 0, 0, 0))
            circle_draw = ImageDraw.Draw(img)
            
            rnd_color = tuple(random.randint(100, 200) for _ in range(3))
            circle_draw.ellipse((0, 0, avatar_size, avatar_size), fill=rnd_color)
            
            letter = author.strip()[0].upper() if author and author.strip() else "?"
            try: letter_font = ImageFont.truetype(self.font_paths.get("bold", self.font_paths.get("regular")), int(avatar_size * 0.45))
            except: letter_font = ImageFont.load_default()
            
            try:
                bbox = circle_draw.textbbox((0, 0), letter, font=letter_font)
                w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
                offset_x, offset_y = bbox[0], bbox[1]
            except AttributeError:
                w, h = circle_draw.textsize(letter, font=letter_font)
                offset_x, offset_y = 0, 0

            circle_draw.text(
                ((avatar_size - w) // 2 - offset_x, (avatar_size - h) // 2 - offset_y),
                letter, font=letter_font, fill=(255, 255, 255)
            )
            canvas.paste(img, avatar_pos, img)

        # 5. Отрисовка текста (С ГРУППИРОВКОЙ)
        text_x = box_x0 + padding + avatar_size + padding
        curr_y = box_y0 + (box_h - total_text_height) // 2
        
        with Pilmoji(canvas, source=AppleEmojiSource) as pilmoji:
            draw = ImageDraw.Draw(canvas)
            for line in lines:
                curr_x = text_x
                
                # Собираем куски обратно в единые строки (так Pilmoji идеально видит baseline для эмодзи)
                grouped_line = []
                for part, font, style, w in line:
                    if not grouped_line:
                        grouped_line.append([part, font, style, w])
                    else:
                        if grouped_line[-1][2] == style and grouped_line[-1][1] == font:
                            grouped_line[-1][0] += part
                            grouped_line[-1][3] += w
                        else:
                            grouped_line.append([part, font, style, w])

                # Рисуем уже нормальными, длинными кусками текста
                for part, font, style, w in grouped_line:
                    if part.strip() or part == ' ':
                        if style.get("code") and part.strip():
                            draw.rounded_rectangle(
                                [curr_x - 2, curr_y - 2, curr_x + w + 2, curr_y + f_size + 4],
                                radius=4, fill=(50, 50, 55, 255)
                            )
                        
                        pilmoji.text((curr_x, curr_y), part, font=font, fill=(255, 255, 255, 255))
                        
                        if style.get("strike") and part.strip():
                            strike_y = curr_y + (f_size // 2) + 2
                            draw.line([(curr_x, strike_y), (curr_x + w, strike_y)], fill=(255, 255, 255, 255), width=2)
                            
                    curr_x += w
                curr_y += f_size + line_spacing
                
            curr_y += gap
            pilmoji.text((text_x, curr_y), author_text, font=f_author, fill=(180, 180, 180, 255))

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
        """[text/reply] - Создать карточку цитаты. Ответьте на сообщение или введите текст."""

        status_id = await mxc_utils.answer(mx, self.strings["processing"])

        try:
            target = await mxc_utils.get_reply_event(mx, event)

            if not target and not text:
                raise UsageError(self.strings["no_reply"])

            sender = target.sender if target else event.sender

            html_payload = ""
            if target:
                if hasattr(target.content, "formatted_body") and target.content.formatted_body:
                    html_payload = self._clean_matrix_html(target.content.formatted_body)
                else:
                    cleaned_body = core_utils.normalize_text(target.content.body or "")
                    html_payload = markdown.markdown(cleaned_body, extensions=['nl2br'])
            else:
                cleaned_text = core_utils.normalize_text(text or "")
                html_payload = markdown.markdown(cleaned_text, extensions=['nl2br'])

            profile = await mxc_utils.get_profile(mx, sender)
            raw_name = profile.displayname
            av_mxc = profile.avatar_url

            name = core_utils.normalize_text(raw_name)

            av_img = None
            if av_mxc:
                try:
                    av_img = await mxc_utils.download(mx, meta=DownloadMeta(url=av_mxc))
                except Exception: pass

            result = await asyncio.to_thread(
                self._generate_payload,
                av_img,
                html_payload,
                name
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
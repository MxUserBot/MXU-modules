#			__  ____  ___   _               _           _   
#			|  \/  \ \/ / | | |___  ___ _ __| |__   ___ | |_ 
#			| |\/| |\  /| | | / __|/ _ \ '__| '_ \ / _ \| __|
#			| |  | |/  \| |_| \__ \  __/ |  | |_) | (_) | |_ 
#			|_|  |_/_/\_\\___/|___/\___|_|  |_.__/ \___/ \__| 
#
# 🔒      Licensed under the GNU AGPLv3
# 🌐 https://www.gnu.org/licenses/agpl-3.0.html


class Meta:
    name = "Chat Export"
    description = "Exports chat history into a ZIP archive with HTML pages, avatars, and media files."
    version = "2.2.0"
    tags = ["utility", "export"]
    author = "https://github.com/PashaHatsune"


import math
import uuid
import asyncio
import zipfile
from collections import Counter
from datetime import datetime
from typing import List, Dict, Any, Optional

from pydantic import BaseModel, Field, ConfigDict, model_validator
from mautrix.types import MessageEvent, EventType
from mautrix.errors import MNotFound

from mxc import utils
from mxc.types import Document
from .. import loader


class ExportPayload(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    room_id: Optional[str] = Field(default=None, description="Target room ID (e.g., !xxxx:matrix.org)")
    limit: int = Field(default=0, ge=0, description="Maximum messages to export (0 = ALL)")
    per_page: int = Field(default=1000, gt=0, description="Messages per HTML file")

    @model_validator(mode='before')
    @classmethod
    def parse_args(cls, v: Any):
        if not isinstance(v, str) or not v.strip():
            return {}
        
        parts = v.strip().split()
        result = {}
        
        queue = parts.copy()
        if queue and queue[0].startswith("!"):
            result["room_id"] = queue.pop(0)
            
        if queue and queue[0].isdigit():
            result["limit"] = int(queue.pop(0))
            
        if queue and queue[0].isdigit():
            result["per_page"] = int(queue.pop(0))
            
        return result


def escape_html(text: str) -> str:
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


class ExportService:
    def __init__(self, mx, room_id: str):
        self.mx = mx
        self.room_id = room_id

    async def get_room_name(self) -> str:
        try:
            name_evt = await self.mx.client.get_state_event(self.room_id, EventType.ROOM_NAME)
            return name_evt.name or self.room_id
        except MNotFound:
            return self.room_id
        except Exception:
            return self.room_id

    async def get_members(self) -> Dict[str, Any]:
        try:
            return await self.mx.client.get_joined_members(self.room_id)
        except Exception:
            return {}
        
    async def fetch_history(self, limit: int) -> List[dict]:
        events =[]
        token = None
        
        while True:
            resp = await utils.fetch_room_messages(
                self.mx, 
                self.room_id, 
                limit=500, 
                from_token=token, 
                direction="b"
            )
            
            raw_chunks = resp.get("chunk",[])
            new_token = resp.get("end")
            
            for evt in raw_chunks:
                if evt.get("type") in ("m.room.message", "m.room.encrypted"):
                    events.append(evt)
            
            if not raw_chunks or not new_token:
                break
            
            token = new_token
            
            if limit > 0 and len(events) >= limit:
                break
                
            await asyncio.sleep(0.2) 
            
        if limit > 0:
            events = events[:limit]
            
        events.reverse()
        return events

    def _generate_html(
        self, events: List[dict], members: Dict[str, Any], page_num: int, 
        total_pages: int, avatars_map: Dict[str, str], media_map: Dict[str, str],
        room_name: str, stats: dict, event_map: Dict[str, dict]
    ) -> str:
        html =[
            "<!DOCTYPE html><html><head><meta charset='utf-8'><title>Chat Export</title><style>",
            "body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background: #e6ebea; margin: 0; padding: 20px; scroll-behavior: smooth; }",
            ".container { max-width: 800px; margin: 0 auto; }",
            ".stats { background: #fff; padding: 20px; border-radius: 12px; margin-bottom: 20px; box-shadow: 0 1px 2px rgba(0,0,0,0.1); border-left: 5px solid #2a5885; }",
            ".stats h2 { margin-top: 0; color: #2a5885; font-size: 20px; }",
            ".stats p, .stats ul { margin: 5px 0; font-size: 14px; color: #333; }",
            ".msg { display: flex; margin-bottom: 15px; }",
            ".avatar { width: 42px; height: 42px; border-radius: 50%; margin-right: 12px; background: #5288c1; flex-shrink: 0; object-fit: cover; }",
            ".avatar-placeholder { width: 42px; height: 42px; border-radius: 50%; margin-right: 12px; background: #5288c1; flex-shrink: 0; }",
            ".content { background: #fff; padding: 8px 12px; border-radius: 12px; border-top-left-radius: 4px; box-shadow: 0 1px 2px rgba(0,0,0,0.1); max-width: 80%; min-width: 30%; }",
            ".header { margin-bottom: 4px; display: flex; align-items: baseline; }",
            ".name { font-weight: 600; color: #2a5885; font-size: 14px; margin-right: 8px; }",
            ".time { color: #999; font-size: 12px; }",
            ".text { font-size: 14px; line-height: 1.4; white-space: pre-wrap; word-wrap: break-word; color: #000; }",
            ".reply-block { background: rgba(42, 88, 133, 0.08); border-left: 3px solid #2a5885; padding: 6px 10px; margin-bottom: 8px; border-radius: 4px; font-size: 13px; }",
            ".reply-author { font-weight: bold; color: #2a5885; margin-bottom: 4px; }",
            ".reply-text { color: #555; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 100%; }",
            ".media-img { max-width: 350px; max-height: 350px; border-radius: 8px; display: block; margin-bottom: 6px; }",
            ".media-file { background: #f0f0f0; padding: 10px; border-radius: 8px; margin-bottom: 6px; display: inline-block; font-weight: 500; text-decoration: none; color: #2a5885; }",
            ".pagination { text-align: center; margin-top: 30px; padding: 20px; background: #fff; border-radius: 8px; box-shadow: 0 1px 2px rgba(0,0,0,0.1); }",
            ".pagination a { display: inline-block; padding: 8px 12px; background: #f0f0f0; text-decoration: none; border-radius: 6px; margin: 0 4px; color: #333; font-size: 14px; }",
            ".pagination a:hover { background: #e0e0e0; }",
            ".pagination b { display: inline-block; padding: 8px 12px; background: #2a5885; color: #fff; border-radius: 6px; margin: 0 4px; font-size: 14px; }",
            ".up-btn { position: fixed; bottom: 20px; right: 20px; background: #2a5885; color: #fff; width: 45px; height: 45px; border-radius: 50%; display: flex; align-items: center; justify-content: center; text-decoration: none; box-shadow: 0 2px 10px rgba(0,0,0,0.2); font-size: 24px; font-weight: bold; transition: 0.2s; opacity: 0.8; }",
            ".up-btn:hover { background: #3b6b9e; opacity: 1; }",
            "</style></head><body><div id='top'></div><div class='container'>"
        ]

        if page_num == 1:
            export_date = datetime.now().strftime('%d.%m.%Y %H:%M:%S')
            
            top_senders_html = ""
            for s, count in stats["top_senders"]:
                m = members.get(s)
                s_name = m.displayname if m and getattr(m, 'displayname', None) else s
                top_senders_html += f"<li><b>{escape_html(s_name)}</b> — <code>{count}</code> сообщений</li>"
                
            html.append(
                f"<div class='stats'>"
                f"<h2>📊 Подробная статистика</h2>"
                f"<p><b>Чат:</b> {escape_html(room_name)}</p>"
                f"<p><b>Участников:</b> {len(members)}</p>"
                f"<p><b>Всего сообщений в архиве:</b> {stats['total_msgs']}</p>"
                f"<p><b>🏆 Топ активных участников:</b></p><ul>{top_senders_html}</ul>"
                f"<p><b>⏰ Пик активности чата:</b> {stats['peak_time']}</p>"
                f"<p><b>💡 Аналитика:</b> <i>{stats['flavor_text']}</i></p>"
                f"<p><b>Дата генерации:</b> {export_date}</p>"
                f"</div>"
            )

        for evt in events:
            sender = evt.get("sender", "Unknown")
            evt_id = evt.get("event_id", "")
            evt_type = evt.get("type", "")
            evt_content = evt.get("content", {})
            msgtype = evt_content.get("msgtype", "")
            
            member = members.get(sender)
            display_name = member.displayname if member and hasattr(member, 'displayname') and member.displayname else sender
            name = escape_html(display_name)
            
            avatar_path = avatars_map.get(sender, "")
            raw_text = evt_content.get("body", "")
            
            # --- Обработка ответов (m.in_reply_to) ---
            reply_html = ""
            relates_to = evt_content.get("m.relates_to", {})
            in_reply_to = relates_to.get("m.in_reply_to", {}).get("event_id")
            
            if in_reply_to:
                # Очистка текста от Matrix fallback (вида "> <@user:domain> текст\n\nСам ответ")
                lines = raw_text.split('\n')
                while lines and lines[0].startswith('>'):
                    lines.pop(0)
                while lines and not lines[0].strip():
                    lines.pop(0)
                raw_text = '\n'.join(lines)
                
                # Блок визуального цитирования
                replied_evt = event_map.get(in_reply_to)
                if replied_evt:
                    rep_sender = replied_evt.get("sender", "Unknown")
                    rep_member = members.get(rep_sender)
                    rep_name = rep_member.displayname if rep_member and getattr(rep_member, 'displayname', None) else rep_sender
                    rep_body = replied_evt.get("content", {}).get("body", "Вложение")
                    
                    if len(rep_body) > 60:
                        rep_body = rep_body[:57] + "..."
                    
                    reply_html = f"<div class='reply-block'><div class='reply-author'>{escape_html(rep_name)}</div><div class='reply-text'>{escape_html(rep_body)}</div></div>"
                else:
                    reply_html = f"<div class='reply-block'><div class='reply-text'><i>Оригинальное сообщение недоступно</i></div></div>"

            text = escape_html(raw_text)
            media_path = media_map.get(evt_id)
            media_html = ""
            
            if media_path:
                if msgtype in ("m.image", "m.sticker"):
                    media_html = f"<a href='{media_path}' target='_blank'><img src='{media_path}' class='media-img'></a>"
                    text = "" 
                elif msgtype == "m.video":
                    media_html = f"<video src='{media_path}' controls class='media-img'></video><br>"
                    text = "" 
                elif msgtype == "m.audio":
                    media_html = f"<audio src='{media_path}' controls style='margin-bottom: 6px;'></audio><br>"
                else:
                    media_html = f"<a href='{media_path}' class='media-file' target='_blank'>📄 Файл ({escape_html(raw_text)})</a><br>"
                    text = ""
            
            if not text and not media_html and not reply_html:
                if evt_type == "m.room.encrypted": text = "<i>[Зашифрованное сообщение]</i>"
                elif msgtype == "m.image": text = "<i>[Фото]</i>"
                elif msgtype == "m.video": text = "<i>[Видео]</i>"
                elif msgtype == "m.audio": text = "<i>[Голосовое сообщение]</i>"
                elif msgtype in ("m.file", "m.sticker"): text = f"<i>[Вложение: {escape_html(raw_text)}]</i>"
                else: text = "<i>[Пустое сообщение]</i>"
            
            ts = evt.get("origin_server_ts", 0) / 1000
            time_str = datetime.fromtimestamp(ts).strftime('%d.%m.%Y %H:%M:%S') if ts else "Unknown"
            av_html = f"<img src='{avatar_path}' class='avatar'>" if avatar_path else "<div class='avatar-placeholder'></div>"
            
            html.append(
                f"<div class='msg'>{av_html}<div class='content'>"
                f"<div class='header'><span class='name'>{name}</span> <span class='time'>{time_str}</span></div>"
                f"{reply_html}<div class='text'>{media_html}{text}</div></div></div>"
            )
            
        html.append("<div class='pagination'>")
        for p in range(1, total_pages + 1):
            if p == page_num: html.append(f"<b>{p}</b> ")
            else: html.append(f"<a href='messages_{p}.html'>{p}</a> ")
        
        html.append("</div></div><a href='#top' class='up-btn'>↑</a></body></html>")
        return "".join(html)

    async def build_zip(self, events: List[dict], members: Dict[str, Any], per_page: int):
        zip_filename = f"chat_export_{uuid.uuid4().hex[:8]}.zip"
        zip_path = utils._get_safe_path(zip_filename)
        
        avatars_map = {}
        media_map = {}
        event_map = {e.get("event_id"): e for e in events if e.get("event_id")}
        room_name = await self.get_room_name()
        
        # --- Сборка статистики ---
        sender_counts = Counter()
        hour_counts = {
            "Ночь (00:00 - 06:00) 🌙": 0,
            "Утро (06:00 - 12:00) 🌅": 0,
            "День (12:00 - 18:00) ☀️": 0,
            "Вечер (18:00 - 00:00) 🌆": 0
        }
        
        for evt in events:
            sender = evt.get("sender")
            if sender:
                sender_counts[sender] += 1
                
            ts = evt.get("origin_server_ts", 0) / 1000
            if ts:
                hr = datetime.fromtimestamp(ts).hour
                if 0 <= hr < 6: hour_counts["Ночь (00:00 - 06:00) 🌙"] += 1
                elif 6 <= hr < 12: hour_counts["Утро (06:00 - 12:00) 🌅"] += 1
                elif 12 <= hr < 18: hour_counts["День (12:00 - 18:00) ☀️"] += 1
                else: hour_counts["Вечер (18:00 - 00:00) 🌆"] += 1
                
        peak_time = max(hour_counts, key=hour_counts.get) if any(hour_counts.values()) else "Неизвестно"
        
        flavor = "Спокойный чат, без лишнего спама."
        if len(events) > 5000:
            flavor = "Очень активный и живой чат! Печатают быстрее, чем я успеваю читать. 🔥"
        elif len(events) > 1000:
            flavor = "Люди любят здесь общаться. Отличное место для бесед. ☕️"
            
        if "Ночь" in peak_time and hour_counts[peak_time] > sum(hour_counts.values()) * 0.4:
            flavor += " Кажется, здесь собрались любители посидеть до поздна! 🦉"

        stats = {
            "top_senders": sender_counts.most_common(3),
            "peak_time": peak_time,
            "total_msgs": len(events),
            "flavor_text": flavor
        }
        
        # --- Создание архива ---
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            
            # Скачиваем аватарки
            unique_senders = set(e.get("sender") for e in events if e.get("sender"))
            for sender in unique_senders:
                member = members.get(sender)
                if member and member.avatar_url:
                    try:
                        data = await self.mx.client.download_media(member.avatar_url)
                        clean_sender = "".join(c for c in sender if c.isalnum())
                        fname = f"assets/avatars/{clean_sender}.png"
                        zf.writestr(fname, data)
                        avatars_map[sender] = fname
                    except Exception: 
                        pass

            # Генерируем HTML страницы
            total_pages = math.ceil(len(events) / per_page) or 1
            for p in range(1, total_pages + 1):
                start_idx = (p - 1) * per_page
                page_events = events[start_idx : start_idx + per_page]
                html = self._generate_html(
                    page_events, members, p, total_pages, avatars_map, media_map, 
                    room_name=room_name, stats=stats, event_map=event_map
                )
                zf.writestr(f"messages_{p}.html", html.encode('utf-8'))
                
        return zip_filename, zip_path


@loader.tds
class ChatExportModule(loader.Module):
    strings = {
        "fetching": "📦 | <b>Fetching messages and compiling archive...</b>",
        "uploading": "☁️ | <b>Uploading massive archive to Matrix...</b>",
        "done": "✅ | <b>Export successful!</b><br>Processed: <code>{count}</code> messages.",
        "empty": "❌ | <b>No messages found.</b>",
        "error": "❌ | <b>Export failed:</b> <code>{err}</code>",
    }

    @loader.command()
    async def export(self, mx, event: MessageEvent, payload: ExportPayload):
        """[!room_id] [limit][per_page] - Export chat history to HTML/ZIP"""
        
        target_room = payload.room_id or event.room_id
        status_id = await utils.answer(mx, self.strings["fetching"], event=event)
        
        service = ExportService(mx, target_room)
        zip_filename = None
        
        try:
            events = await service.fetch_history(limit=payload.limit)
            if not events:
                await utils.answer(mx, self.strings["empty"], edit_id=status_id)
                return
                
            members = await service.get_members()
            zip_filename, zip_path = await service.build_zip(events, members, payload.per_page)
            
            await utils.answer(mx, self.strings["uploading"], edit_id=status_id)
            
            # Получаем размер файла безопасно через pathlib
            file_size = zip_path.stat().st_size
            
            async def file_generator(path):
                with open(path, "rb") as f:
                    while True:
                        chunk = await asyncio.to_thread(f.read, 1024 * 1024 * 2)
                        if not chunk:
                            break
                        yield chunk
            
            mxc_url = await mx.client.upload_media(
                data=file_generator(zip_path),
                mime_type="application/zip",
                filename="ChatExport.zip"
            )

            await utils.answer(
                mx,
                media=Document(
                    url=mxc_url,
                    mimetype="application/zip",
                    size=file_size,
                    filename="ChatExport.zip",
                    caption=self.strings["done"].format(count=len(events))
                ),
                edit_id=status_id
            )
            
        except Exception as e:
            await utils.answer(mx, self.strings["error"].format(err=str(e)), edit_id=status_id)
        finally:
            # Безопасное удаление файла через utils 
            if zip_filename:
                await utils.safe_remove(zip_filename)
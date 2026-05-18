import time
from datetime import datetime, timezone
from pathlib import Path

from mautrix.types import EventType, MessageType
from mxc import utils, types
from mxc.types.media import Image, Video, Audio, Document
from .. import loader, utils as cutils


class Meta:
    name = "SaveDeleteMessages"
    description = "Saving deleted messages. Use this module with caution, because you might get punched in the face for saving deleted messages. :)"
    version = "1.1.0"
    tags = ["security", "utility"]


@loader.tds
class SaveDeleteMessagesModule(loader.Module):
    """Module for intercepting and restoring deleted messages."""

    strings = {
        "redacted": "🗑 | <b>Message deleted!</b><br><br>📍 | <b>From chat:</b> <a href='https://matrix.to/#/{room}'><code>{room}</code></a><br>👤 | <b>Sender:</b> <a href='https://matrix.to/#/{user}'><code>{user}</code></a><br>🕐 | <b>Sent:</b> <code>{sent}</code><br>🗑 | <b>Deleted:</b> <code>{deleted}</code><br>💬 | <b>Text:</b><br><blockquote>{text}</blockquote>",
        "cfg_ttl": "How many hours to store message history in the database?",
        "cfg_watch_rooms": "WHERE TO WATCH: 'all' (all chats) or a comma-separated list of !room_ids.",
        "cfg_log_dest": "WHERE TO SEND: 'log' (system log room), 'current' (same chat), or !room_id.",
        "cfg_save_media": "Enable saving media from deleted messages",
        "cfg_save_photo": "Save images",
        "cfg_save_video": "Save videos",
        "cfg_save_document": "Save documents (files)",
        "cfg_save_audio": "Save audio",
        "cfg_max_media_mb": "Max media file size in MB to save (0 = no limit)",
    }

    config = {
        "ttl_hours": loader.ConfigValue(24, strings["cfg_ttl"]),
        "watch_rooms": loader.ConfigValue("all", strings["cfg_watch_rooms"]),
        "log_destination": loader.ConfigValue("log", strings["cfg_log_dest"]),
        "save_media": loader.ConfigValue(True, strings["cfg_save_media"]),
        "save_photo": loader.ConfigValue(True, strings["cfg_save_photo"]),
        "save_video": loader.ConfigValue(True, strings["cfg_save_video"]),
        "save_document": loader.ConfigValue(False, strings["cfg_save_document"]),
        "save_audio": loader.ConfigValue(False, strings["cfg_save_audio"]),
        "max_media_mb": loader.ConfigValue(5, strings["cfg_max_media_mb"]),
    }

    @loader.on(EventType.ROOM_MESSAGE)
    async def message_watcher(self, mx, event):
        if event.sender == mx.client.mxid:
            return

        watch_cfg = self.config["watch_rooms"].strip().lower()
        if watch_cfg != "all":
            allowed_rooms = [r.strip() for r in watch_cfg.replace("\n", ",").split(",") if r.strip()]
            if event.room_id not in allowed_rooms:
                return

        rel = event.content.relates_to
        if rel and getattr(rel, "rel_type", None) == "m.replace":
            return

        mtype = event.content.msgtype
        is_media = mtype in (MessageType.IMAGE, MessageType.VIDEO, MessageType.FILE, MessageType.AUDIO)

        data = {
            "u": str(event.sender),
            "t": event.content.body,
            "ts": event.timestamp,
            "r": str(event.room_id),
            "p": None,
            "m": None,
            "w": None,
            "h": None,
            "mt": str(mtype) if is_media else None,
        }

        if is_media and self.config["save_media"]:
            mtype_str = str(mtype)
            type_ok = (
                (mtype_str == "m.image" and self.config["save_photo"]) or
                (mtype_str == "m.video" and self.config["save_video"]) or
                (mtype_str == "m.file" and self.config["save_document"]) or
                (mtype_str == "m.audio" and self.config["save_audio"])
            )
            if type_ok:
                info = getattr(event.content, "info", None) or {}
                size = getattr(info, "size", 0) or 0
                max_mb = self.config["max_media_mb"]
                if max_mb <= 0 or size <= max_mb * 1024 * 1024:
                    try:
                        dl = await utils.download(mx, types.DownloadMeta(url=event))
                        pth = await cutils.safe_save(dl.url, filename=dl.filename)
                        data["p"] = str(pth)
                        data["m"] = dl.mimetype or getattr(info, "mimetype", None)
                        data["w"] = getattr(info, "w", None)
                        data["h"] = getattr(info, "h", None)
                    except Exception:
                        pass

        await self._set(f"msg:{event.event_id}", data)

    @loader.on(EventType.ROOM_REDACTION)
    async def redaction_handler(self, mx, event):
        target_id = event.redacts
        cached = await self._get(f"msg:{target_id}")
        if not cached:
            return

        sent_ts = cached.get("ts", 0)
        sent_str = (
            datetime.fromtimestamp(sent_ts / 1000, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
            if sent_ts else "Unknown"
        )
        del_ts = event.timestamp
        del_str = (
            datetime.fromtimestamp(del_ts / 1000, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
            if del_ts else "Unknown"
        )

        text = self.strings["redacted"].format(
            room=cached.get("r", "Unknown"),
            user=cached["u"],
            sent=sent_str,
            deleted=del_str,
            text=cutils.escape_html(cached["t"])
        )

        log_cfg = self.config["log_destination"].strip().lower()
        if log_cfg == "log":
            destinations = [mx.log_room]
        elif log_cfg == "current":
            destinations = [event.room_id]
        else:
            destinations = [r.strip() for r in log_cfg.replace("\n", ",").split(",") if r.strip().startswith("!")]

        filepath = cached.get("p")
        mtype_str = cached.get("mt")
        mimetype = cached.get("m")

        for room_id in destinations:
            if not room_id:
                continue
            try:
                if filepath and mtype_str and Path(filepath).exists():
                    with open(filepath, "rb") as f:
                        raw = f.read()
                    fn = Path(filepath).name
                    if mtype_str == "m.image":
                        media = Image(url=raw, mimetype=mimetype, w=cached.get("w"), h=cached.get("h"), filename=fn)
                    elif mtype_str == "m.video":
                        media = Video(url=raw, mimetype=mimetype, w=cached.get("w"), h=cached.get("h"), filename=fn)
                    elif mtype_str == "m.audio":
                        media = Audio(url=raw, mimetype=mimetype, filename=fn)
                    else:
                        media = Document(url=raw, mimetype=mimetype, filename=fn)
                    await utils.answer(mx, text=text, media=media, room_id=room_id)
                else:
                    await utils.answer(mx, text, room_id=room_id)
            except Exception as e:
                raise e


        await self._set(f"msg:{target_id}", None)

    @loader.cron("1h")
    async def cleanup_cron(self, mx):
        now = int(time.time())
        ttl_sec = self.config["ttl_hours"] * 3600

        if not hasattr(self, "_db") or not self._db:
            return

        try:
            data_map = self._db.items()
            to_del = [
                key for key, val in data_map.items()
                if key.startswith("msg:") and isinstance(val, dict) and (now - val.get("ts", 0) > ttl_sec)
            ]
            for key in to_del:
                cached = await self._get(key)
                if cached and cached.get("p"):
                    try:
                        Path(cached["p"]).unlink(missing_ok=True)
                    except Exception:
                        pass
                await self._set(key, None)
        except Exception as e:
            raise e

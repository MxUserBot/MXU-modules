#			__  ____  ___   _               _           _   
#			|  \/  \ \/ / | | |___  ___ _ __| |__   ___ | |_ 
#			| |\/| |\  /| | | / __|/ _ \ '__| '_ \ / _ \| __|
#			| |  | |/  \| |_| \__ \  __/ |  | |_) | (_) | |_ 
#			|_|  |_/_/\_\\___/|___/\___|_|  |_.__/ \___/ \__| 
#
# 🔒      Licensed under the GNU AGPLv3
# 🌐 https://www.gnu.org/licenses/agpl-3.0.html

import time
from datetime import datetime, timezone

from mautrix.types import EventType, MessageType
from mxc import utils
from .. import loader


class Meta:
    name = "SaveDeleteMessages"
    description = "Saving deleted messages. Use this module with caution, because you might get punched in the face for saving deleted messages. :)"
    version = "1.0.8"
    tags = ["security", "utility"]


@loader.tds
class SaveDeleteMessagesModule(loader.Module):
    """Module for intercepting and restoring deleted messages."""

    strings = {
"redacted": "🗑 | <b>Message deleted!</b><br><br>📍 | <b>From chat:</b> <a href='https://matrix.to/#/{room}'><code>{room}</code></a><br>👤 | <b>Sender:</b> <a href='https://matrix.to/#/{user}'><code>{user}</code></a><br>🕐 | <b>Sent:</b> <code>{sent}</code><br>🗑 | <b>Deleted:</b> <code>{deleted}</code><br>💬 | <b>Text:</b><br><blockquote>{text}</blockquote>",        "cfg_ttl": "How many hours to store message history in the database?",
        "cfg_watch_rooms": "WHERE TO WATCH: 'all' (all chats) or a comma-separated list of !room_ids.",
        "cfg_log_dest": "WHERE TO SEND: 'log' (system log room), 'current' (same chat), or !room_id.",
    }

    config = {
        "ttl_hours": loader.ConfigValue(24, strings["cfg_ttl"]),
        "watch_rooms": loader.ConfigValue("all", strings["cfg_watch_rooms"]),
        "log_destination": loader.ConfigValue("log", strings["cfg_log_dest"]),
    }


    @loader.on(EventType.ROOM_MESSAGE)
    async def message_watcher(self, mx, event):
        if not event.content or event.content.msgtype != MessageType.TEXT:
            return

        if event.sender == mx.client.mxid:
            return

        watch_cfg = self.config["watch_rooms"].strip().lower()
        if watch_cfg != "all":
            allowed_rooms = [r.strip() for r in watch_cfg.replace("\n", ",").split(",") if r.strip()]
            if event.room_id not in allowed_rooms:
                return

        rel = getattr(event.content, "relates_to", None)
        if rel and getattr(rel, "rel_type", None) == "m.replace":
            return

        data = {
            "u": str(event.sender),
            "t": event.content.body,
            "ts": event.timestamp,
            "r": str(event.room_id)
        }
        
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
            text=utils.escape_html(cached["t"])
        )

        log_cfg = self.config["log_destination"].strip().lower()
        
        if log_cfg == "log":
            destinations = [mx.log_room]
        elif log_cfg == "current":
            destinations = [event.room_id]
        else:
            destinations = [
                r.strip() 
                for r in log_cfg.replace("\n", ",").split(",") 
                if r.strip().startswith("!")
            ]

        for room_id in destinations:
            if not room_id:
                continue
            try:
                await utils.answer(mx, text, room_id=room_id)
            except Exception as e:
                self.log.error(f"AntiRecall send error ({room_id}): {e}")
        
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
                await self._set(key, None)
        except Exception as e:
            self.log.error(f"AntiRecall cleanup error: {e}")
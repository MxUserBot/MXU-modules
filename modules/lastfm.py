import asyncio
from typing import Optional, Dict

from pydantic import BaseModel
from mautrix.types import MessageEvent

from ...core import loader, utils


class Meta:
    name = "LastFM"
    description = "Last.fm synchronization for Matrix RPC."
    version = "3.0.0"
    tags = ["music", "rpc"]
    author = "@pasha:pashahatsune.pp.ua"


class SongData(BaseModel):
    artist: str
    track: str
    album: str
    song_url: str
    image_bytes: Optional[bytes] = None

    @property
    def display_text(self) -> str:
        return f"{self.artist} — {self.track}"


class LastFMEngine:
    @staticmethod
    async def fetch_now_playing(
        api_key: str, 
        username: str, 
        strings: Dict[str, str]
    ) -> Optional[SongData]:
        url = "http://ws.audioscrobbler.com/2.0/"
        params = {
            "method": "user.getrecenttracks",
            "user": username,
            "api_key": api_key,
            "format": "json",
            "limit": 1
        }

        try:
            data = await utils.request(url, params=params)
            track_list = data.get("recenttracks", {}).get("track", [])
            if not track_list:
                return None
            
            track = track_list[0]
            is_playing = track.get("@attr", {}).get("nowplaying") == "true"
            if not is_playing:
                return None

            artist = track["artist"]["#text"]
            name = track["name"]
            album = track.get("album", {}).get("#text", "Unknown Album")
            song_url = track.get("url", "")
            
            images = track.get("image", [])
            cover_url = images[-1]["#text"] if images else None
            
            img_bytes = None
            if cover_url and cover_url.strip():
                try:
                    img_bytes = await utils.request(cover_url, return_type="bytes")
                except:
                    pass

            return SongData(
                artist=artist,
                track=name,
                album=album,
                song_url=song_url,
                image_bytes=img_bytes
            )
        except Exception:
            return None


@loader.tds
class LastFMModule(loader.Module):
    strings = {
        "config_saved": "✅ |<b>Last.fm username updated to:</b> <code>{user}</code>",
        "now_playing": "🎶 | <b>Now Playing:</b> <code>{track}</code>",
        "not_playing": "❌ | <b>Currently not playing anything on Last.fm.</b>",
        "auto_started": "✅ | <b>Last.fm auto-update started!</b>",
        "auto_stopped": "🛑 | <b>Last.fm auto-update stopped.</b>",
        "api_error": "❌ | <b>Last.fm API unreachable.</b>"
    }

    config = {
        "api_key": loader.ConfigValue(
            default="460cda35be2fbf4f28e8ea7a38580730",
            description="Last.fm API Key",
            required=True
        ),
        "username": loader.ConfigValue(
            default="MikuSv0",
            description="Last.fm Username",
            required=True
        ),
        "interval": loader.ConfigValue(
            default=15,
            description="Update interval in seconds",
            validator=lambda x: isinstance(x, int) and x >= 5
        ),
        "default_cover": loader.ConfigValue(
            default="mxc://pashahatsune.pp.ua/Pog8OuodZbmX73kEHCO1V77VDh6ctM8e",
            description="Default MXC for cover art if none found"
        )
    }

    def __init__(self):
        self._bg_task: Optional[asyncio.Task] = None
        self._last_track_id: Optional[str] = None


    async def _matrix_start(self, mx):
        await self._start_loop(mx)


    def _matrix_stop(self, mx):
        self._stop_loop()


    async def _start_loop(self, mx):
        self._stop_loop()
        self._bg_task = asyncio.create_task(self._auto_update_loop(mx))


    def _stop_loop(self):
        if self._bg_task:
            self._bg_task.cancel()
            self._bg_task = None


    async def _auto_update_loop(self, mx):
        while True:
            try:
                song = await LastFMEngine.fetch_now_playing(
                    self.config["api_key"],
                    self.config["username"],
                    self.strings
                )

                if song:
                    current_id = f"{song.artist}:{song.track}"
                    if current_id != self._last_track_id:
                        self._last_track_id = current_id
                        await utils.set_rpc_media(
                            mx,
                            artist=song.artist,
                            album=song.album,
                            track=song.track,
                            cover_art=song.image_bytes or self.config["default_cover"],
                            player="Last.fm",
                            streaming_link=song.song_url
                        )
                else:
                    if self._last_track_id is not None:
                        self._last_track_id = None
                        await utils.clear_rpc(mx)

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"LastFM Loop Error: {e}")
            
            await asyncio.sleep(self.config["interval"])


    @loader.command()
    async def lfconfig(self, mx, event: MessageEvent, username: str):
        """<username> | Update Last.fm target account"""
        self.config.set("username", username)
        await utils.answer(mx, self.strings["config_saved"].format(user=username))


    @loader.command()
    async def np(self, mx, event: MessageEvent):
        """| Display currently playing track from Last.fm"""
        song = await LastFMEngine.fetch_now_playing(
            self.config["api_key"],
            self.config["username"],
            self.strings
        )
        
        if not song:
            return await utils.answer(mx, self.strings["not_playing"])
            
        text = utils.escape_html(song.display_text)
        await utils.answer(mx, self.strings["now_playing"].format(track=text))


    @loader.command()
    async def lfauto(self, mx, event: MessageEvent):
        """| Manually trigger background RPC update loop"""
        await self._start_loop(mx)
        await utils.answer(mx, self.strings["auto_started"])


    @loader.command()
    async def lfstop(self, mx, event: MessageEvent):
        """| Terminate background RPC update loop"""
        self._stop_loop()
        await utils.answer(mx, self.strings["auto_stopped"])
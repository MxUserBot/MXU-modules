import asyncio
import os
import tempfile
from mautrix.types import MessageEvent

from ...core import loader, utils


class Meta:
    name = "LastFMModule"
    _cls_doc = "Отображение текущей музыки из LastFM с анимацией обложки"
    version = "1.2.0"
    tags = ["music"]


@loader.tds
class LastFMModule(loader.Module):
    """Модуль для трансляции текущего трека из LastFM (Now Playing)"""

    strings = {
        "no_args": "Использование: <code>.lfconfig username</code>",
        "no_username": "<b>[LastFM]</b> Имя пользователя не настроено. Используй <code>.lfconfig &lt;username&gt;</code>",
        "config_saved": "<b>[LastFM]</b> Никнейм <code>{}</code> успешно сохранен!",
        "now_playing": "🎶 | <b>Playing:</b> <code>{}</code>",
        "not_playing": "<b>[LastFM]</b> Сейчас ничего не играет.",
        "auto_started": "<b><u>[LastFM]</u></b> Автообновление статуса запущено!",
        "auto_stopped": "<b>[LastFM]</b> Автообновление остановлено.",
        "error": "<b>[LastFM]</b> Ошибка: <code>{}</code>"
    }

    def __init__(self):
        self.bg_task = None

    async def make_rotating_apng(self, image_bytes: bytes) -> bytes:
        """Создает вращающуюся WebP обложку через FFmpeg"""
        size, duration, fps = 512, 6, 30
        radius = size // 2

        with tempfile.TemporaryDirectory() as tmpdir:
            in_path = os.path.join(tmpdir, "input.jpg")
            out_path = os.path.join(tmpdir, "output.webp")

            with open(in_path, "wb") as f:
                f.write(image_bytes)

            filters = (
                f"crop='min(iw,ih):min(iw,ih)',scale={size}:{size}:flags=lanczos,format=rgba,"
                f"geq=r='r(X,Y)':a='if(gt(hypot(X-{radius},Y-{radius}),{radius}),0,alpha(X,Y))',"
                f"rotate='2*PI*t/{duration}:bilinear=1:c=0x00000000:ow={size}:oh={size}'"
            )

            cmd = [
                'ffmpeg', '-y', '-loop', '1', '-i', in_path, '-vf', filters,
                '-t', str(duration), '-r', str(fps), '-vcodec', 'libwebp',
                '-lossless', '0', '-compression_level', '6', '-q:v', '70',
                '-loop', '0', '-an', out_path
            ]

            process = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            await process.communicate()

            if process.returncode != 0:
                return b""

            try:
                with open(out_path, "rb") as f:
                    return f.read()
            except FileNotFoundError:
                return b""

    async def get_current_song(self) -> dict | None:
        """Получает инфо о треке и генерирует анимацию обложки"""
        username = await self._get("username")
        api_key = await self._get("api_key")

        if not username or not api_key:
            return None

        url = "http://ws.audioscrobbler.com/2.0/"
        params = {
            "method": "user.getrecenttracks",
            "user": username,
            "api_key": api_key,
            "format": "json",
            "limit": 1
        }

        data = await utils.request(url, params=params)
        if not data:
            return None

        tracks = data.get("recenttracks", {}).get("track", [])
        if not tracks:
            return None

        track = tracks[0]
        is_playing = track.get("@attr", {}).get("nowplaying") == "true"
        if not is_playing:
            return None

        artist = track.get("artist", {}).get("#text", "Unknown Artist")
        name = track.get("name", "Unknown Track")
        album = track.get("album", {}).get("#text", "Unknown Album")
        song_url = track.get("url", "")
        
        images = track.get("image", [])
        cover_url = images[-1].get("#text") if images else None

        if cover_url:
            img_bytes = await utils.request(cover_url, return_type="bytes")


        return {
            "text": f"{artist} — {name}",
            "image": img_bytes,
            "artist": artist,
            "track": name,
            "album": album,
            "song_url": song_url
        }

    @loader.command()
    async def lfconfig(self, mx, event: MessageEvent):
        """<username> - Установить LastFM никнейм"""
        args = utils.get_args_raw(event)
        if not args:
            return await utils.answer(mx, self.strings["no_args"])

        username = args.strip()
        await self._set("username", username)
        await utils.answer(mx, self.strings["config_saved"].format(utils.escape_html(username)))

    @loader.command()
    async def np(self, mx, event: MessageEvent):
        """Узнать текущий играющий трек"""
        if not await self._get("username"):
            return await utils.answer(mx, self.strings["no_username"])

        song = await self.get_current_song()
        if not song:
            return await utils.answer(mx, self.strings["not_playing"])
            
        text = self.strings["now_playing"].format(utils.escape_html(song["text"]))
        await utils.answer(mx, text)

    @loader.command()
    async def lfauto(self, mx, event: MessageEvent):
        """Запустить автообновление играющего трека (RPC)"""
        if not await self._get("username"):
            return await utils.answer(mx, self.strings["no_username"])

        if self.bg_task and not self.bg_task.done():
            self.bg_task.cancel()

        await utils.answer(mx, self.strings["auto_started"])
        self.bg_task = asyncio.create_task(self._auto_update_loop(mx))

    @loader.command()
    async def lfstop(self, mx, event: MessageEvent):
        """Остановить автообновление"""
        if self.bg_task:
            self.bg_task.cancel()
            self.bg_task = None
        await utils.answer(mx, self.strings["auto_stopped"])

    async def _auto_update_loop(self, mx):
        last_song_text = None

        while True:
            try:
                current_song = await self.get_current_song()
                current_text = current_song["text"] if current_song else None
                
                if current_text != last_song_text:
                    last_song_text = current_text

                    if current_song:
                        await utils.set_rpc_media(
                            mx,
                            artist=current_song["artist"],
                            album=current_song["album"],
                            track=current_song["track"],
                            cover_art=current_song["image"] or "mxc://pashahatsune.pp.ua/Pog8OuodZbmX73kEHCO1V77VDh6ctM8e",
                            player="Last.fm",
                            streaming_link=current_song["song_url"]
                        )
                    else:
                        await utils.set_rpc_activity(mx, name="Ничего не играет", details="idle")

                await asyncio.sleep(15)

            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"[LastFM Error]: {e}")
                await asyncio.sleep(20)

    async def _matrix_start(self, mx):
        """Вызывается ядром при загрузке модуля"""
        if not await self._get("api_key"):
            await self._set("api_key", "460cda35be2fbf4f28e8ea7a38580730")
            
        if not await self._get("username"):
            await self._set("username", "MikuSv0")

        self.bg_task = asyncio.create_task(self._auto_update_loop(mx))
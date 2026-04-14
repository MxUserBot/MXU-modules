import asyncio
import logging
from telethon import TelegramClient, events
from mautrix.types import MessageEvent, TextMessageEventContent, RoomDirectoryVisibility
from ...core import loader, utils

logger = logging.getLogger("TG_PM_Bridge")

class Meta:
    name = "TelegramPMBridge"
    _cls_doc = "Мост для всех ЛС Telegram с фоновой синхронизацией и Пространствами."
    version = "3.1.0"
    dependencies = ["telethon"]
    tags = ["bridge", "pm"]

@loader.tds
class TelegramPMBridgeModule(loader.Module):
    config = {
        "API_ID": 23281546,
        "API_HASH": "1485b7f21956a05dff9fa3bc9e1a2fd0"
    }

    def __init__(self):
        super().__init__()
        self.tg_client = None
        self._mx = None
        self._is_ready = False
        self._last_bridged_text = None
        self._is_syncing = False

    async def _matrix_start(self, mx):
        self._mx = mx
        
        # База данных: маппинг { "tg_user_id": "matrix_room_id" }
        self.pm_mappings = await self._get("pm_mappings", {})
        self.space_id = await self._get("tg_space_id", None)

        uid = "default"
        if hasattr(self._mx, "user_id"):
            uid = self._mx.user_id.split(':')[0].replace("@", "")
            
        self.tg_client = TelegramClient(f"tg_session_{uid}", int(self.config["API_ID"]), self.config["API_HASH"])
        
        asyncio.create_task(self.start_bridge())

    async def start_bridge(self):
        try:
            await self.tg_client.connect()
            if await self.tg_client.is_user_authorized():
                # Слушаем только ЛИЧНЫЕ сообщения
                self.tg_client.add_event_handler(self.on_tg_message, events.NewMessage(func=lambda e: e.is_private))
                self._is_ready = True
                logger.info(f"PM-Мост запущен. В базе чатов: {len(self.pm_mappings)}")
            else:
                logger.error("Телеграм не авторизован.")
        except Exception as e:
            logger.error(f"Ошибка старта моста: {e}")


    async def _create_pm_room(self, tg_user_id: int, title: str) -> str:
            """Создает комнату и добавляет её в Space"""
            new_room_id = await self._mx.client.create_room(
                name=f"TG | {title}",
                visibility=RoomDirectoryVisibility.PRIVATE,
                is_direct=True
            )
            
            if self.space_id:
                my_id = getattr(self._mx.client, "mxid", getattr(self._mx, "user_id", ""))
                my_domain = my_id.split(":")[1] if ":" in my_id else "matrix.org"
                
                try:
                    await self._mx.client.send_state_event(
                        room_id=self.space_id,
                        event_type="m.space.child",
                        state_key=new_room_id,
                        content={"via": [my_domain]}
                    )
                except Exception as e:
                    logger.error(f"Не удалось добавить комнату {new_room_id} в Space: {e}")

            self.pm_mappings[str(tg_user_id)] = str(new_room_id)
            await self._set("pm_mappings", self.pm_mappings)
            
            return new_room_id

    async def _background_sync(self, mx, reply_room_id):
        """Фоновая задача для перебора всех ЛС"""
        try:
            if not self.space_id:
                self.space_id = await mx.client.create_room(
                    name="Telegram PMs",
                    creation_content={"type": "m.space"},
                    visibility=RoomDirectoryVisibility.PRIVATE
                )
                await self._set("tg_space_id", self.space_id)
                logger.info(f"Создан Space: {self.space_id}")

            count = 0
            async for dialog in self.tg_client.iter_dialogs():
                if not self._is_syncing:
                    break

                if dialog.is_user:
                    entity = dialog.entity
                    if getattr(entity, 'bot', False) or getattr(entity, 'deleted', False):
                        continue
                        
                    tg_user_id = str(entity.id)
                    
                    if tg_user_id in self.pm_mappings:
                        continue # Комната уже существует
                        
                    name = getattr(entity, 'first_name', '') or ''
                    last = getattr(entity, 'last_name', '') or ''
                    title = f"{name} {last}".strip() or f"User {tg_user_id}"

                    await self._create_pm_room(entity.id, title)
                    count += 1
                    
                    await asyncio.sleep(2)

            if self._is_syncing:
                await mx.client.send_text(reply_room_id, f"✅ Фоновая синхронизация завершена!\nНовых комнат создано: {count}")
        except Exception as e:
            logger.error(f"Ошибка фоновой синхронизации: {e}", exc_info=True)
            await mx.client.send_text(reply_room_id, f"❌ Ошибка во время синхронизации: {e}")
        finally:
            self._is_syncing = False

    @loader.command()
    async def tgsync(self, mx, event: MessageEvent):
        """
        Запустить полную синхронизацию всех ЛС.
        """
        if self._is_syncing:
            return await utils.answer(mx, "⏳ Синхронизация уже идет! Пожалуйста, дождитесь окончания.")

        self._is_syncing = True
        await utils.answer(mx, "🔄 Запущена фоновая синхронизация всех личных сообщений...\nИз-за лимитов Matrix это займет некоторое время (около 2-х секунд на 1 чат). Я пришлю уведомление сюда, когда закончу.")
        
        asyncio.create_task(self._background_sync(mx, event.room_id))

    async def on_tg_message(self, event):
        """TG -> Matrix"""
        if not event.text: return
        
        if event.out and event.text == self._last_bridged_text:
            self._last_bridged_text = None
            return

        try:
            sender = await event.get_sender()
            tg_user_id = str(sender.id)
            
            # Авто-создание комнаты для тех, кто написал впервые после tgsync
            if tg_user_id not in self.pm_mappings:
                name = getattr(sender, 'first_name', '') or ''
                last = getattr(sender, 'last_name', '') or ''
                title = f"{name} {last}".strip() or f"User {tg_user_id}"
                
                await self._create_pm_room(sender.id, title)
                
            room_id = self.pm_mappings[tg_user_id]

            name = getattr(sender, 'first_name', 'TG_User')
            plain_text = f"[{name}]: {event.text}"
            html_text = f"<b>[{name}]</b>: {event.text}"

            await self._mx.client.send_text(room_id, plain_text, html=html_text)

        except Exception as e:
            logger.error(f"Ошибка TG->Matrix: {e}")

    async def _matrix_message(self, mx, event: MessageEvent):
        """Matrix -> TG"""
        if not isinstance(event.content, TextMessageEventContent) or not self._is_ready:
            return

        matrix_to_tg = {v: k for k, v in self.pm_mappings.items()}
        current_room = str(event.room_id)
        
        if current_room not in matrix_to_tg:
            return

        target_tg_id = int(matrix_to_tg[current_room])

        prefixes = await mx.get_prefix()
        if isinstance(prefixes, list): prefixes = tuple(prefixes)
        my_id = mx.client.mxid if hasattr(mx.client, "mxid") else getattr(mx, "user_id", None)

        if event.content.body.startswith(prefixes): return
        if str(event.sender) != str(my_id): return
        if event.content.body.startswith("[") and "]:" in event.content.body: return

        if self.tg_client and await self.tg_client.is_user_authorized():
            try:
                self._last_bridged_text = event.content.body
                await self.tg_client.send_message(target_tg_id, event.content.body)
            except Exception as e:
                logger.error(f"Ошибка Matrix->TG: {e}")
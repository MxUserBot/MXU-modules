import asyncio
from mautrix.types import MessageEvent

from ...core import loader, utils


class Meta:
    name = "TextToImage"
    description = "Превращает текстовое сообщение в картинку (m.text -> m.image)"
    version = "1.1.0"
    tags = ["fun", "media"]


@loader.tds
class TextToImageModule(loader.Module):
    
    @loader.command()
    async def magic(self, mx, event: MessageEvent):
        """- превратить это сообщение в картинку через 2 секунды"""
        
        # 1. Редактируем саму команду в статус загрузки
        await utils.answer(
            mx, 
            "1", 
            event=event, 
            edit_id=event.event_id
        )
        
        # 2. Ждем 2 секунды
        await asyncio.sleep(2)
        
        # 3. Твой MXC URL
        mxc_url = "mxc://pashahatsune.pp.ua/DUdVAMG7QaWXXHBHbjT7Uj0QzZzSij9s"
        
        # 4. Формируем payload. 
        # Чтобы убрать рамки и искажения, мы указываем параметры "w" и "h".
        # Также мы меняем msgtype на m.image на верхнем уровне.
        
        image_info = {
            "mimetype": "image/png",
            "w": 1200,  # Ширина картинки
            "h": 600,   # Высота картинки
            "size": 0   # Можно оставить 0 или не указывать
        }

        edit_payload = {
            "msgtype": "m.image",
            "body": "magic_image.png",
            "url": mxc_url,
            "info": image_info,
            "m.new_content": {
                "msgtype": "m.image",
                "body": "magic_image.png",
                "url": mxc_url,
                "info": image_info
            },
            "m.relates_to": {
                "rel_type": "m.replace",
                "event_id": event.event_id
            }
        }
        
        # 5. Отправляем
        await mx.client.send_message(event.room_id, edit_payload)
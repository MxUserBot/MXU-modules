#			__  ____  ___   _               _           _   
#			|  \/  \ \/ / | | |___  ___ _ __| |__   ___ | |_ 
#			| |\/| |\  /| | | / __|/ _ \ '__| '_ \ / _ \| __|
#			| |  | |/  \| |_| \__ \  __/ |  | |_) | (_) | |_ 
#			|_|  |_/_/\_\\___/|___/\___|_|  |_.__/ \___/ \__| 
#
# 🔒      Licensed under the GNU AGPLv3
# 🌐 https://www.gnu.org/licenses/agpl-3.0.html


import asyncio
import random
from pydantic import BaseModel

from mxc import utils
from .. import loader
from ..core.langs import Locales, current


class Meta:
    name = "MatrixTrollPack"
    description = "Troll animation pack. Disclaimer: This is a joke module. It is not intended to offend anyone, not the creators of the Matrix, but anyone else. Do not use on sensitive people. Remove this module."
    version = "1.4.0"
    tags = ["fun"]


class Strings(BaseModel):
    hack_prog: str
    hack_done: str
    hack_dl: str
    hack_end: str
    
    drugs_prog: str
    drugs_found: str
    drugs_hit: str
    drugs_endings: list[str]
    
    
    stupid_start: str
    stupid_anim: list[str]
    
    bombs_anim: list[str]
    
    call_start: str
    call_anim: list[str]
    
    kill_start: str
    kill_anim: list[str]
    
    zv_error: str


locales = Locales(
    ru=Strings(
        hack_prog="Ищу фалы про тебя нахуй {}%",
        hack_done="Нашел про тебя файлы!",
        hack_dl="⬇️ Скачиваю... {}%",
        hack_end="🐓 нашли файлы что ты петух!",
        
        drugs_prog="💊 Поиск мега-шпекса в кэше Element... {}%",
        drugs_found="🚬 Найдено 3 гигабайта хуйни",
        drugs_hit="🌿⚗️ Оформляем матрикс-вкид ебать",
        drugs_endings=[
            '😳 Вас откачали, пиздец, БОЛЬШЕ НЕ ЮЗАЙ ЭТОТ ТОРМОЗНОЙ ELEMENT',
            '🥴 Ты поймал 429 TOO MANY REQUESTS НАХУЙ, ебашь ещё один вкид',
            '😖 ФЕДЕРАЦИЯ ОТВАЛИЛАСЬ НАХУЙ. Причина смерти - ебучий Synapse сожрал всю оперативку',
            '😌 Оформил вкид, E2EE ключи встали как надо, заебись'
        ],
                
        stupid_start="тупой еблан",
        stupid_anim=[
            "<pre><code><b>ТВОЙ МОЗГ</b> ➡️ 🧠\n\n🧠         (^_^)🗑</code></pre>",
            "<pre><code><b>ТВОЙ МОЗГ</b> ➡️ 🧠\n\n🧠     (^_^)    🗑</code></pre>",
            "<pre><code><b>ТВОЙ МОЗГ</b> ➡️ 🧠\n\n🧠 (^_^)        🗑</code></pre>",
            "<pre><code><b>ТВОЙ МОЗГ</b> ➡️ 🧠\n\n(> ^_^)>🧠         🗑</code></pre>",
            "<pre><code><b>ТВОЙ МОЗГ</b> ➡️ 🧠\n\n    (> ^_^)>🧠     🗑</code></pre>",
            "<pre><code><b>ТВОЙ МОЗГ</b> ➡️ 🧠\n\n        (> ^_^)>🧠 🗑</code></pre>",
            "<pre><code><b>МОЗГ ПРОЕБАН НАХУЙ</b> ➡️ ❌\n\n           < (^_^ <)🗑</code></pre>",
        ],
        
        bombs_anim=[
            "▪️▪️▪️▪️ <br>▪️▪️▪️▪️ <br>▪️▪️▪️▪️ <br>",
            "💣💣💣💣 <br>▪️▪️▪️▪️ <br>▪️▪️▪️▪️ <br>",
            "▪️▪️▪️▪️ <br>▪️▪️▪️▪️ <br>💣💣💣💣 <br>",
            "▪️▪️▪️▪️ <br>💥💥💥💥 <br>💥💥💥💥 <br>",
            "<b>ДОМБИМ! СЕРВЕР ЛЕЖИТ НАХУЙ......</b>"
        ],
        
        call_start="Звоню Мэттью Ходжсону (Создателю Матрикса)......",
        call_anim=[
            "<b>Подключение к Element HQ блять...</b>",
            "<b>Менеджер: АЛЛО БЛЯТЬ, У НАС СЕРВАК УПАЛ, КТО ЗВОНИТ?</b>",
            "<b>Я: Йоу, позови Мэттью, тут пиздец</b>",
            "<b>Звоню Matthew </b>  <code>по федерации</code>",
            "<b>Я: Здарова, сноси аккаунт этому хуесосу нахуй.</b>",
            "<b>Matthew: ЕБАТЬ!!! Ща дам ему 429 M_LIMIT_EXCEEDED на всю жизнь.</b>",
            "<b>Matthew: АЛЛО, ПОМОГИ, SYNAPSE ПАДАЕТ, ОЗУ КОНЧИЛАСЬ АААААА</b>",
            "<b>Я: Переписывай на Rust еблан, я отключаюсь.</b>",
            "<b>[M_UNKNOWN] Приватный звонок упал нахуй.</b>",
        ],
        
        kill_start="ТЕБЕ ПИЗДААААА, ФЕДЕРАЦИЯ ПАДАЕТ!",
        kill_anim=[
            "<pre><code>Ｆｉｉｉｉｉｒｅ\n(　･ิω･ิ)︻デ═一==>\n====>____________</code></pre>",
            "<pre><code>======>__________\n========>\n==========></code></pre>",
            "<pre><code>============>\n==============>\n======>;(^。^)ノ</code></pre>",
            "<b>АККАУНТ НАХУЙ УНИЧТОЖЕН (°̥̥̥̥̥̥̥̥•̀.̫•́°̥̥̥̥̥̥̥)</b>",
        ],
        
        zv_error="❌ Дай текст, хуесос",
    ),
    en=Strings(
        hack_prog="💻 Hacking the fucking Synapse server... {}%",
        hack_done="✅ SERVER FUCKING HACKED! E2EE KEYS STOLEN!",
        hack_dl="⬇️ Dumping a shitload of keys... {}%",
        hack_end="🐓 DECRYPTED YOUR CHATS - YOU ARE A FUCKING FURRY FAGGOT!",
        
        drugs_prog="💊 Searching for shit in Element cache... {}%",
        drugs_found="🚬 Found 3 GB of logs",
        drugs_hit="🌿⚗️ Taking a Matrix hit",
        drugs_endings=[
            '😳 Resuscitated! STOP USING THIS SLOW ASS ELECTRON ELEMENT',
            '🥴 You got 429 TOO MANY REQUESTS FUCK, hit it again',
            '😖 FEDERATION BROKE DOWN. Cause of death - Synapse ate all the RAM',
            '😌 Took a hit, E2EE keys are verified, feels fucking awesome'
        ],
        
        
        stupid_start="stupid fuck",
        stupid_anim=[
            "<pre><code><b>YOUR BRAIN</b> ➡️ 🧠\n\n🧠         (^_^)🗑</code></pre>",
            "<pre><code><b>YOUR BRAIN</b> ➡️ 🧠\n\n🧠     (^_^)    🗑</code></pre>",
            "<pre><code><b>YOUR BRAIN</b> ➡️ 🧠\n\n🧠 (^_^)        🗑</code></pre>",
            "<pre><code><b>YOUR BRAIN</b> ➡️ 🧠\n\n(> ^_^)>🧠         🗑</code></pre>",
            "<pre><code><b>YOUR BRAIN</b> ➡️ 🧠\n\n    (> ^_^)>🧠     🗑</code></pre>",
            "<pre><code><b>YOUR BRAIN</b> ➡️ 🧠\n\n        (> ^_^)>🧠 🗑</code></pre>",
            "<pre><code><b>FUCKING BRAIN LOST</b> ➡️ ❌\n\n           < (^_^ <)🗑</code></pre>",
        ],
        
        bombs_anim=[
            "▪️▪️▪️▪️ <br>▪️▪️▪️▪️ <br>▪️▪️▪️▪️ <br>",
            "💣💣💣💣 <br>▪️▪️▪️▪️ <br>▪️▪️▪️▪️ <br>",
            "▪️▪️▪️▪️ <br>▪️▪️▪️▪️ <br>💣💣💣💣 <br>",
            "▪️▪️▪️▪️ <br>💥💥💥💥 <br>💥💥💥💥 <br>",
            "<b>BOMBING! SERVER IS DOWN FUCK......</b>"
        ],
        
        call_start="Calling Matthew Hodgson (Matrix CEO)......",
        call_anim=[
            "<b>Connecting To Element HQ fuck...</b>",
            "<b>Element HQ: HELLO FUCK, OUR SERVER CRASHED, WHO IS THIS?</b>",
            "<b>Me: Yo, call Matthew, it's a disaster here</b>",
            "<b>Calling Matthew </b>  <code>via federation</code>",
            "<b>Me: Hello Sir, nuke this guy's account.</b>",
            "<b>Matthew : HOLY SHIT!!! I'll give him 429 M_LIMIT_EXCEEDED for life.</b>",
            "<b>Matthew : HELP, SYNAPSE IS CRASHING, OUT OF RAM AAAAAA</b>",
            "<b>Me: Rewrite it in Rust idiot, I'm disconnecting.</b>",
            "<b>[M_UNKNOWN] Private Call dropped.</b>",
        ],
        
        kill_start="YOU ARE FUCKED, FEDERATION IS CRASHING!",
        kill_anim=[
            "<pre><code>Ｆｉｉｉｉｉｒｅ\n(　･ิω･ิ)︻デ═一==>\n====>____________</code></pre>",
            "<pre><code>======>__________\n========>\n==========></code></pre>",
            "<pre><code>============>\n==============>\n======>;(^。^)ノ</code></pre>",
            "<b>ACCOUNT FUCKING NUKED (°̥̥̥̥̥̥̥̥•̀.̫•́°̥̥̥̥̥̥̥)</b>",
        ],
        
        zv_error="❌ Give me some text, fucker",
    )
)


@loader.tds
class TrollPackModule(loader.Module):
    strings = locales

    @loader.command()
    async def hack(self, mx, event):
        """Взломать Synapse / Hack Synapse"""
        msg_id = await utils.answer(mx, "...", event=event)
        
        for perc in [0, 100]:
            text = self.strings.get("hack_prog").format(perc)
            await utils.answer(mx, text, edit_id=msg_id)
            await asyncio.sleep(1.5)
            
        await utils.answer(mx, self.strings.get("hack_done"), edit_id=msg_id)
        await asyncio.sleep(2)
        
        for perc in [0, 100]:
            text = self.strings.get("hack_dl").format(perc)
            await utils.answer(mx, text, edit_id=msg_id)
            await asyncio.sleep(1.5)
            
        await utils.answer(mx, self.strings.get("hack_end"), edit_id=msg_id)


    @loader.command()
    async def drugs(self, mx, event):
        """Поиск шпекса / Find drugs"""
        msg_id = await utils.answer(mx, "...", event=event)
        
        for perc in [0, 100]:
            text = self.strings.get("drugs_prog").format(perc)
            await utils.answer(mx, text, edit_id=msg_id)
            await asyncio.sleep(2.0)
            
        await utils.answer(mx, self.strings.get("drugs_found"), edit_id=msg_id)
        await asyncio.sleep(2)
        
        await utils.answer(mx, self.strings.get("drugs_hit"), edit_id=msg_id)
        await asyncio.sleep(3)
        
        endings = self.strings.get("drugs_endings")
        await utils.answer(mx, random.choice(endings), edit_id=msg_id)


    @loader.command()
    async def stupid(self, mx, event):
        """Твой мозг анимация / Your brain animation"""
        msg_id = await utils.answer(mx, self.strings.get("stupid_start"), event=event)
        anim = self.strings.get("stupid_anim")
        
        for frame in anim:
            await asyncio.sleep(1.0)
            await utils.answer(mx, frame, edit_id=msg_id)

    @loader.command()
    async def bombs(self, mx, event):
        """Бомбежка / Bombs animation"""
        msg_id = await utils.answer(mx, "...", event=event)
        anim = self.strings.get("bombs_anim")
        
        for frame in anim:
            await utils.answer(mx, frame, edit_id=msg_id)
            await asyncio.sleep(1.0)

    @loader.command()
    async def call(self, mx, event):
        """Позвонить Мэттью / Call Matthew"""
        msg_id = await utils.answer(mx, self.strings.get("call_start"), event=event)
        anim = self.strings.get("call_anim")
        
        for frame in anim:
            await asyncio.sleep(3)  
            await utils.answer(mx, frame, edit_id=msg_id)

    @loader.command()
    async def kill(self, mx, event):
        """Убить аккаунт / Kill animation"""
        msg_id = await utils.answer(mx, self.strings.get("kill_start"), event=event)
        await asyncio.sleep(2)
        
        anim = self.strings.get("kill_anim")
        for frame in anim:
            await asyncio.sleep(2)
            await utils.answer(mx, frame, edit_id=msg_id)
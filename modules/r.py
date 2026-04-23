import re
import time
import asyncio
from typing import Optional, Dict, Any

from pydantic import BaseModel, model_validator, ConfigDict
from mautrix.types import MessageEvent, EventType

from ...core import loader, utils


class Meta:
    name = "Currency"
    description = "automated currency conversion"
    version = "2.0.0"
    tags = ["money", "api"]
    author = "@pasha:pashahatsune.pp.ua"


class ConvertPayload(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    
    amount: float
    from_c: str
    to_c: Optional[str] = None

    @model_validator(mode='before')
    @classmethod
    def parse_convert(cls, v: Any):
        if isinstance(v, str):
            # Filtering out words like "to", "in", "в"
            parts = [p for p in v.split() if p.lower() not in ["в", "to", "in", "into"]]
            if len(parts) < 2:
                raise ValueError("Insufficient arguments")
            
            # Clean numeric value
            raw_val = parts[0].replace(" ", "").replace(",", ".")
            return {
                "amount": float(raw_val),
                "from_c": parts[1].lower(),
                "to_c": parts[2].lower() if len(parts) >= 3 else None
            }
        return v


class CurrencyEngine:
    CACHE = {}
    LAST_UPDATE = 0
    
    MAP = {
        "$": "usd", "dollar": "usd", "dollars": "usd", "бакс": "usd", "баксов": "usd", "доллар": "usd", "долларов": "usd",
        "€": "eur", "euro": "eur", "евро": "eur",
        "₽": "rub", "ruble": "rub", "rubles": "rub", "руб": "rub", "рубль": "rub", "рублей": "rub", "деревянных": "rub",
        "£": "gbp", "pound": "gbp", "фунт": "gbp",
        "₿": "btc", "bitcoin": "btc", "биток": "btc", "биткоин": "btc",
        "ton": "ton", "тон": "ton", "toncoin": "ton",
        "eth": "eth", "эфир": "eth", "ethereum": "eth",
        "usdt": "usdt", "тезер": "usdt",
        "¥": "cny", "yuan": "cny", "юань": "cny",
        "₴": "uah", "грн": "uah", "гривна": "uah", "гривен": "uah",
        "₸": "kzt", "тенге": "kzt", "тг": "kzt"
    }

    @classmethod
    def resolve_code(cls, raw: str) -> str:
        raw = re.sub(r'[?!)!.,]', '', raw.lower().strip())
        return cls.MAP.get(raw, raw)

    @classmethod
    async def get_rates(cls, base: str) -> Optional[Dict[str, float]]:
        now = time.time()
        if now - cls.LAST_UPDATE < 600 and base in cls.CACHE:
            return cls.CACHE[base]

        url = f"https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@latest/v1/currencies/{base}.json"
        try:
            data = await utils.request(url, return_type="json")
            if data and base in data:
                cls.CACHE[base] = data[base]
                cls.LAST_UPDATE = now
                return data[base]
        except:
            pass
        return None


@loader.tds
class CurrencyModule(loader.Module):
    strings = {
        "conv_res": "💱 <b>{val} {from_c}</b> ➜ <b>{res} {to_c}</b>",
        "about": "<b>💠 Currency Engine v{version}</b><br>Auto-conversion active: <code>{auto}</code>",
        "err_not_found": "❌ <b>Currency not found:</b> <code>{code}</code>",
        "err_api": "❌ <b>API Error:</b> Rates unavailable."
    }

    config = {
        "target": loader.ConfigValue("USD", "Default target currency"),
        "auto_convert": loader.ConfigValue(False, "Enable auto-conversion in messages"),
        "min_value": loader.ConfigValue(0.1, "Minimum numeric value to convert"),
        "work_mode": loader.ConfigValue(
            "all", 
            "Mode: 'all', 'whitelist', or 'blacklist'",
            validator=lambda x: x.lower() in ["all", "whitelist", "blacklist"]
        ),
        "room_list": loader.ConfigValue([], "List of room IDs for white/blacklist")
    }

    @loader.command()
    async def currency(self, mx, event: MessageEvent):
        """| Show module information"""
        await utils.answer(mx, self.strings["about"].format(
            version=Meta.version,
            auto=self.config["auto_convert"]
        ))

    @loader.command()
    async def convert(self, mx, event: MessageEvent, payload: ConvertPayload):
        """<amount> <from> [to] | Manual currency conversion"""
        from_code = CurrencyEngine.resolve_code(payload.from_c)
        to_code = CurrencyEngine.resolve_code(payload.to_c or self.config["target"])

        rates = await CurrencyEngine.get_rates(from_code)
        if not rates or to_code not in rates:
            return await utils.answer(mx, self.strings["err_not_found"].format(code=to_code))

        res = round(payload.amount * rates[to_code], 2)
        await utils.answer(mx, self.strings["conv_res"].format(
            val=payload.amount,
            from_c=from_code.upper(),
            res=f"{res:,}".replace(",", " "),
            to_c=to_code.upper()
        ))

    @loader.on(EventType.ROOM_MESSAGE)
    async def watcher(self, mx, event: MessageEvent):
        """Automated message scanning for currency triggers"""
        if not self.config["auto_convert"] or event.sender == mx.client.mxid:
            return

        mode = self.config["work_mode"].lower()
        rooms = self.config["room_list"]
        
        if mode == "whitelist" and event.room_id not in rooms:
            return
        if mode == "blacklist" and event.room_id in rooms:
            return

        text = event.content.body
        if not text:
            return

        pattern = r"(?:([$€£¥₽₿])\s*(\d+(?:[\s.,]\d+)*))|(?:(\d+(?:[\s.,]\d+)*)\s*([$€£¥₽₿₴₸A-Za-zа-яёА-ЯЁ]+))"
        matches = re.findall(pattern, text)
        if not matches:
            return

        target_code = self.config["target"].lower()
        results = []

        for m in matches:
            raw_val = m[1] if m[0] else m[2]
            raw_curr = m[0] if m[0] else m[3]

            amount = float(raw_val.replace(" ", "").replace(",", "."))
            if amount < self.config["min_value"]:
                continue

            curr_code = CurrencyEngine.resolve_code(raw_curr)
            if curr_code == target_code:
                continue

            rates = await CurrencyEngine.get_rates(curr_code)
            if rates and target_code in rates:
                res = round(amount * rates[target_code], 2)
                results.append(self.strings["conv_res"].format(
                    val=amount,
                    from_c=curr_code.upper(),
                    res=f"{res:,}".replace(",", " "),
                    to_c=target_code.upper()
                ))

        if results:
            await utils.answer(mx, "<br>".join(results), event=event)
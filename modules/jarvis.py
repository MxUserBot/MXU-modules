from typing import Any, Optional

from mautrix.types import MessageEvent
from pydantic import BaseModel, Field, model_validator, ConfigDict

from ...core import loader, utils


class Meta:
    name = "JarvisModule"
    _cls_doc = "Jarvis (AI assist)"
    version = "1.1.0"
    tags = ["ai"]
    author = "@pasha:pashahatsune.pp.ua"


class JarvisPayload(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    query: str = Field(default="")

    @model_validator(mode='before')
    @classmethod
    def parse_query(cls, v: Any):
        return {"query": v.strip()} if isinstance(v, str) else {"query": ""}


class Jarvis:
    def __init__(self, api_key: str, base_url: str, model: str, system_prompt: str):
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self.system_prompt = system_prompt


    async def ask(self, query: str) -> str:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": query}
            ]
        }

        try:
            resp = await utils.request(
                self.base_url,
                method="POST",
                json=payload,
                headers=headers
            )
            
            if not resp or "choices" not in resp:
                return f"❌ AI Provider Error: {resp}"
                
            return resp["choices"][0]["message"]["content"]
            
        except Exception as e:
            return f"❌ Service Failure: {str(e)}"


@loader.tds
class JarvisModule(loader.Module):
    config = {
        "api_key": loader.ConfigValue("lm-studio", "OpenAI API Key", required=True),
        "base_url": loader.ConfigValue("http://192.168.1.128:1234/v1/chat/completions", "API Endpoint"),
        "model": loader.ConfigValue("gpt-4o", "AI Model"),
        "trigger_word": loader.ConfigValue("хуйлан", "Trigger word (for legacy purposes, changed in watcher)"),
        "system_prompt": loader.ConfigValue(
            "Ты — дерзкий ИИ-помощник Джарвис. Отвечай кратко, саркастично и по делу.", 
            "AI Personality"
        )
    }

    strings = {
        "thinking": "⏳ | <b>Jarvis is processing...</b>",
        "no_query": "❓ | <b>Speak up, I can't hear your thoughts yet.</b>"
    }

    def __init__(self):
        self.ai: Optional[Jarvis] = None


    async def _matrix_start(self, mx):
        self.ai = Jarvis(
            api_key=self.config.get("api_key"),
            base_url=self.config.get("base_url"),
            model=self.config.get("model"),
            system_prompt=self.config.get("system_prompt")
        )


    @loader.command()
    async def jarvis(self, mx, event: MessageEvent, payload: JarvisPayload):
        """<query> - Direct AI interaction"""
        if not payload.query:
            return await utils.answer(mx, self.strings["no_query"])

        await utils.answer(mx, self.strings["thinking"])
        response = await self.ai.ask(payload.query)
        await utils.answer(mx, f"<b>Jarvis:</b> {response}")
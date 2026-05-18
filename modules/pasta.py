from random import randint

from faker import Faker

from ..core import loader
from mxc import utils


class Meta:
    name = "Pasta"
    description = "fun fake dox"
    version = "1.0.0"
    tags = ["fun"]
    dependencies = ["faker"]


@loader.tds
class PastaModule(loader.Module):
    strings = {
        "name": "Pasta",
        "doxx": "<b>🔴 Докс на тя:</b><br><br>{}<br><br><i>Жди докс бошеее</i>",
    }

    @loader.command()
    async def doxx(self, mx, event):
        """- generate random fake doxxing pasta"""
        fake = Faker("ru_RU")
        name = "Артур Ламаев" if randint(0, 1) == 0 else fake.name()
        lines = [
            f"ФИО : {name}",
            f"Адрес электронной почты : {fake.email()}",
            f"Телефон : {fake.phone_number()}",
            f"Адрес регистрации : {fake.street_address()}",
            f"Пароль к почте : {fake.password()}",
            f"Карта : {fake.credit_card_full()}",
            f"Паспорт : {fake.passport_number()}",
        ]
        await utils.answer(mx, self.strings["doxx"].format("<br>".join(lines)))

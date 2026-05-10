#			__  ____  ___   _               _           _   
#			|  \/  \ \/ / | | |___  ___ _ __| |__   ___ | |_ 
#			| |\/| |\  /| | | / __|/ _ \ '__| '_ \ / _ \| __|
#			| |  | |/  \| |_| \__ \  __/ |  | |_) | (_) | |_ 
#			|_|  |_/_/\_\\___/|___/\___|_|  |_.__/ \___/ \__| 
#
# 🔒      Licensed under the GNU AGPLv3
# 🌐 https://www.gnu.org/licenses/agpl-3.0.html


class Meta:
    name = "AskFSM"
    description = "FSM demo: ask name and age interactively"
    version = "1.0.0"
    tags = ["examples", "fsm"]


from mautrix.types import MessageEvent
from mxc.fsm import FSMContext, State, StatesGroup
from mxc import utils
from .. import loader


class AskStates(StatesGroup):
    name = State()
    age = State()


@loader.tds
class AskFSMModule(loader.Module):
    strings = {
        "start": "👋 | <b>Let's get to know you!</b><br>What's your name?",
        "ask_age": "Nice to meet you, <b>{name}</b>!<br>How old are you?",
        "invalid_age": "❌ | <b>{value}</b> is not a valid age. Please enter a number.",
        "done": (
            "✅ | <b>Done!</b><br><br>"
            "📋 <b>Your info:</b><br>"
            "• Name: <b>{name}</b><br>"
            "• Age: <b>{age}</b><br><br>"
            "Type <code>.ask</code> again to restart."
        ),
        "cancelled": "❌ | <b>Cancelled.</b>",
    }

    @loader.command()
    async def ask(self, mx, event: MessageEvent):
        """Start the FSM registration dialog"""
        await utils.answer(mx, self.strings["start"])
        mx.fsm.set_state(event, AskStates.name)


    @loader.state(AskStates.name)
    async def ask_name(self, mx, event: MessageEvent, ctx: FSMContext):
        name = event.content.body.strip()
        if not name:
            return

        await ctx.update_data(name=name)
        await ctx.set_state(AskStates.age)
        await utils.answer(
            mx,
            self.strings["ask_age"].format(name=name),
            event=event,
        )

    @loader.state(AskStates.age)
    async def ask_age(self, mx, event: MessageEvent, ctx: FSMContext):
        raw = event.content.body.strip()
        if not raw.isdigit():
            await utils.answer(
                mx,
                self.strings["invalid_age"].format(value=raw),
                event=event,
            )
            return

        data = await ctx.get_data()
        await ctx.clear()

        await utils.answer(
            mx,
            self.strings["done"].format(name=data["name"], age=raw),
            event=event,
        )

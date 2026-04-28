from typing import Literal

from mautrix.types import MessageEvent
from pydantic import BaseModel, Field

from ...core import loader, utils
from ...core.types import FSMContext, State, StatesGroup


class Meta:
    name = "StateManagementExample"
    description = "Demonstrates loader.state and FSMContext"
    version = "2.3.0"
    tags = ["example", "fsm", "state"]


class SurveyStates(StatesGroup):
    name = State()
    age = State()
    color = State()
    confirm = State()


class FeedbackStates(StatesGroup):
    rating = State()
    comment = State()


@loader.tds
class StateManagementExampleModule(loader.Module):
    strings = {
        "survey_start": "📝 Let's create a profile. What is your name?",
        "survey_age": "Nice to meet you, {name}. How old are you?",
        "survey_color": "Got it. What is your favorite color?",
        "survey_confirm": (
            "<b>Profile summary</b><br>"
            "name = <code>{name}</code><br>"
            "age = <code>{age}</code><br>"
            "color = <code>{color}</code><br><br>"
            "Reply with <code>yes</code> or <code>no</code>."
        ),
        "survey_done": "✅ Profile saved.",
        "survey_cancelled": "❌ Survey cancelled.",
        "feedback_start": "⭐ Rate the bot from 1 to 5.",
        "feedback_comment": "✍️ Leave a comment or send <code>-</code>.",
        "feedback_done": "✅ Feedback saved. Rating: <code>{rating}/5</code>.",
    }

    @loader.command()
    async def survey(
        self,
        mx,
        event: MessageEvent,
        action: Literal["start", "cancel"] = "start",
    ):
        """[start/cancel] - start or cancel the profile survey"""
        state = FSMContext(mx.fsm, event)

        if action == "cancel":
            await state.clear()
            await utils.answer(mx, self.strings["survey_cancelled"])
            return

        await state.clear()
        await state.set_state(SurveyStates.name)
        await utils.answer(mx, self.strings["survey_start"])

    @loader.state(SurveyStates.name)
    async def process_survey_name(
        self,
        mx,
        event,
        state: FSMContext,
        name: str = Field(min_length=1, max_length=32)
,
    ):
        await state.update_data(name=name)
        await state.set_state(SurveyStates.age)
        await event.reply(self.strings["survey_age"].format(name=name))

    @loader.state(SurveyStates.age)
    async def process_survey_age(
        self,
        mx,
        event,
        state: FSMContext,
        age: int = Field(ge=1, le=120)
,
    ):
        await state.update_data(age=age)
        await state.set_state(SurveyStates.color)
        await event.reply(self.strings["survey_color"])

    @loader.state(SurveyStates.color)
    async def process_survey_color(
        self,
        mx,
        event,
        state: FSMContext,
        color: str = "unknown"
,
    ):
        data = await state.get_data()

        await state.update_data(color=color)
        await state.set_state(SurveyStates.confirm)
        await event.reply(
            self.strings["survey_confirm"].format(
                name=data["name"],
                age=data["age"],
                color=color,
            )
        )

    @loader.state(SurveyStates.confirm)
    async def process_survey_confirm(
        self,
        mx,
        event,
        state: FSMContext,
        answer: Literal["yes", "y", "да", "no", "n", "нет", "cancel"]
,
    ):
        if answer in {"no", "n", "нет", "cancel"}:
            await state.clear()
            await event.reply(self.strings["survey_cancelled"])
            return

        data = await state.get_data()
        await state.clear()
        await event.reply(self.strings["survey_done"])
        self.logger.info(f"Saved survey payload: {data}")

    @loader.command()
    async def feedback(self, mx, event: MessageEvent):
        """start a feedback flow"""
        state = FSMContext(mx.fsm, event)
        await state.clear()
        await state.set_state(FeedbackStates.rating)
        await utils.answer(mx, self.strings["feedback_start"])

    @loader.state(FeedbackStates.rating)
    async def process_feedback_rating(
        self,
        mx,
        event,
        state: FSMContext,
        rating: int = Field(ge=1, le=5)
,
    ):
        await state.update_data(rating=rating)
        await state.set_state(FeedbackStates.comment)
        await event.reply(self.strings["feedback_comment"])

    @loader.state(FeedbackStates.comment)
    async def process_feedback_comment(
        self,
        mx,
        event,
        state: FSMContext,
        comment: str = ""
,
    ):
        data = await state.get_data()
        saved_comment = "" if comment.strip() == "-" else comment

        await state.clear()
        await event.reply(
            self.strings["feedback_done"].format(rating=data["rating"])
        )
        self.logger.info(
            "Saved feedback payload: "
            f"rating={data['rating']} comment={saved_comment}"
        )

    @loader.command()
    async def cancel_survey(self, mx, event: MessageEvent):
        """cancel current FSM state"""
        state = FSMContext(mx.fsm, event)
        await state.clear()
        await utils.answer(mx, self.strings["survey_cancelled"])

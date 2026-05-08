from mautrix.types import MessageEvent
from ..core import loader, utils
from ..core.utils.emoji import EmojiKeyBoard

class Meta:
    name = "EmojiCallbacks"
    description = "Examples for reaction-driven pages, choices, confirmations and ratings"
    version = "3.0.0"
    tags = ["examples", "callbacks", "ui"]

@loader.tds
class PagesModule(loader.Module):
    strings = {
        "page_1": (
            "<b>📖 Emoji pages (Page 1)</b><br><br>"
            "Matrix has no inline buttons, but reactions carry<br>"
            "<code>m.relates_to.key</code> used as a tiny callback key."
        ),
        "page_2": (
            "<b>⚙️ Emoji pages (Page 2)</b><br><br>"
            "Same runtime works for confirmations, action menus and any "
            "other stateful flow."
        ),
        "page_3": (
            "<b>🧩 Emoji pages (Page 3)</b><br><br>"
            "A sticker is just an <code>m.sticker</code> event. "
            "No callback event fires on click — reactions are the sane path."
        ),
        "choice": (
            "<b>🍵 Choice demo</b><br><br>"
            "Should this action be executed?<br>"
            "✅ yes / ❌ no / 🤔 later"
        ),
        "choice_result": "<b>Choice:</b> <code>{choice}</code>",
        "actions": (
            "<b>🧪 Generic action menu</b><br><br>"
            "🔄 refresh counter<br>"
            "ℹ️ show payload<br>"
            "🧹 close menu<br><br>"
            "Counter: <code>{count}</code>"
        ),
        "payload": (
            "<b>🧪 Generic action menu</b><br><br>"
            "Payload can be any Python object kept in memory.<br>"
            "Last payload: <code>{payload}</code><br><br>"
            "Counter: <code>{count}</code>"
        ),
        "closed": "<b>🧹 Menu closed.</b>",
        "confirm_title": (
            "<b>⚠️ Confirm action</b><br><br>"
            "Are you sure you want to proceed?"
        ),
        "confirm_done": "<b>✅ Action confirmed!</b>",
        "confirm_cancelled": "<b>❌ Action cancelled.</b>",
        "rating_title": "<b>⭐ Rate this demo</b><br><br>How many stars?",
        "rating_result": "<b>⭐ Your rating:</b> <code>{stars}/5</code>",
        "qpage_1": "<b>📄 Quick page 1</b><br><br>Manual prev/next via <code>EmojiKeyBoard</code>.",
        "qpage_2": "<b>📄 Quick page 2</b><br><br>Two buttons, same message — edit in callback.",
        "qpage_3": "<b>📄 Quick page 3</b><br><br><code>remove_clicked=False</code> keeps reactions.",
        "poll_title": "<b>📊 Quick poll</b><br><br>What's your favourite language?",
        "poll_result": "<b>📊 Poll results</b><br><br>{}\n\nTotal votes: <code>{total}</code>",
    }

    @loader.command()
    async def pages(self, mx, event: MessageEvent):
        """Show reaction-driven pages"""
        pages_list = [
            self.strings["page_1"],
            self.strings["page_2"],
            self.strings["page_3"]
        ]

        async def page_handler(ctx: utils.EmojiCallbackContext):
            current = (ctx.data.get("page", 0) + 1) % len(pages_list)
            ctx.data["page"] = current
            await ctx.edit(pages_list[current])

        markup = EmojiKeyBoard(
            rows=[[utils.EmojiButton(emoji="➡️", data="next")]],
            callback=page_handler,
            data={"page": 0},
            remove_clicked=False,
        )

        await utils.answer(
            mx,
            pages_list[0],
            event=event,
            reply_markup=markup
        )

    @loader.command()
    async def quickpages(self, mx, event: MessageEvent):
        """Quick pagination — prev/next via EmojiKeyBoard"""
        pages = [
            self.strings["qpage_1"],
            self.strings["qpage_2"],
            self.strings["qpage_3"],
        ]

        async def on_click(ctx: utils.EmojiCallbackContext):
            page = ctx.data["page"]
            if ctx.payload == "prev":
                page = (page - 1) % len(pages)
            else:
                page = (page + 1) % len(pages)
            ctx.data["page"] = page
            await ctx.edit(pages[page])

        markup = EmojiKeyBoard(
            rows=[[
                utils.EmojiButton(emoji="⬅️", data="prev"),
                utils.EmojiButton(emoji="➡️", data="next"),
            ]],
            callback=on_click,
            data={"page": 0},
            remove_clicked=False,
        )

        await utils.answer(mx, pages[0], event=event, reply_markup=markup)

    @loader.command()
    async def choose(self, mx, event: MessageEvent):
        """Show yes/no/later choice"""
        async def on_choice(ctx: utils.EmojiCallbackContext) -> None:
            await ctx.edit(
                self.strings["choice_result"].format(
                    choice=utils.escape_html(str(ctx.payload)),
                )
            )
            await ctx.close(clear_reactions=True)

        markup = utils.EmojiKeyBoard(
            rows=[[
                utils.EmojiButton(emoji="✅", data="yes"),
                utils.EmojiButton(emoji="❌", data="no"),
                utils.EmojiButton(emoji="🤔", data="later")
            ]],
            callback=on_choice,
            single_use=True
        )

        await utils.answer(mx, self.strings["choice"], event=event, reply_markup=markup)

    @loader.command()
    async def confirm(self, mx, event: MessageEvent):
        """Confirm or cancel an action"""
        async def on_confirm(ctx: utils.EmojiCallbackContext) -> None:
            if ctx.payload == "yes":
                await ctx.edit(self.strings["confirm_done"])
            else:
                await ctx.edit(self.strings["confirm_cancelled"])
            await ctx.close(clear_reactions=True)

        markup = EmojiKeyBoard(
            rows=[[
                utils.EmojiButton(emoji="✅", data="yes"),
                utils.EmojiButton(emoji="❌", data="no"),
            ]],
            callback=on_confirm,
            single_use=True,
        )

        await utils.answer(mx, self.strings["confirm_title"], event=event, reply_markup=markup)

    @loader.command()
    async def rate(self, mx, event: MessageEvent):
        """Rate 1–5 stars via EmojiKeyBoard"""
        async def on_rate(ctx: utils.EmojiCallbackContext) -> None:
            await ctx.edit(
                self.strings["rating_result"].format(stars=ctx.payload),
            )
            await ctx.close(clear_reactions=True)

        markup = EmojiKeyBoard(
            rows=[[
                utils.EmojiButton(emoji="⭐", data=1),
                utils.EmojiButton(emoji="⭐⭐", data=2),
                utils.EmojiButton(emoji="⭐⭐⭐", data=3),
                utils.EmojiButton(emoji="⭐⭐⭐⭐", data=4),
                utils.EmojiButton(emoji="⭐⭐⭐⭐⭐", data=5),
            ]],
            callback=on_rate,
            single_use=True,
        )

        await utils.answer(mx, self.strings["rating_title"], event=event, reply_markup=markup)

    @loader.command()
    async def poll(self, mx, event: MessageEvent):
        """Quick poll — EmojiKeyBoard with vote counting"""
        votes = {}

        async def on_vote(ctx: utils.EmojiCallbackContext) -> None:
            nonlocal votes
            votes[ctx.payload] = votes.get(ctx.payload, 0) + 1
            lines = [f"<code>{k}</code>: {'█' * min(v, 20)} {v}" for k, v in votes.items()]
            total = sum(votes.values())
            await ctx.edit(
                self.strings["poll_result"].format(
                    "<br>".join(lines), total=total
                )
            )

        markup = EmojiKeyBoard(
            rows=[[
                utils.EmojiButton(emoji="🐍", data="Python"),
                utils.EmojiButton(emoji="🦀", data="Rust"),
                utils.EmojiButton(emoji="☕", data="Java"),
                utils.EmojiButton(emoji="💧", data="Go"),
            ]],
            callback=on_vote,
            remove_clicked=False,
        )

        await utils.answer(mx, self.strings["poll_title"], event=event, reply_markup=markup)

    @loader.command()
    async def actions(self, mx, event: MessageEvent):
        """Show generic emoji action payloads"""
        async def on_action(ctx: utils.EmojiCallbackContext) -> None:
            action = ctx.payload["action"]

            if action == "refresh":
                ctx.data["count"] = ctx.data.get("count", 0) + 1
                await ctx.edit(self.strings["actions"].format(count=ctx.data["count"]))
                return

            if action == "payload":
                await ctx.edit(
                    self.strings["payload"].format(
                        payload=utils.escape_html(str(ctx.payload)),
                        count=ctx.data.get("count", 0),
                    )
                )
                return

            if action == "close":
                await ctx.edit(self.strings["closed"])
                await ctx.close(clear_reactions=True)

        markup = utils.EmojiKeyBoard(
            rows=[
                [
                    utils.EmojiButton(emoji="🔄", data={"action": "refresh"}),
                    utils.EmojiButton(emoji="ℹ️", data={"action": "payload"}),
                ],
                [utils.EmojiButton(emoji="🧹", data={"action": "close"})]
            ],
            callback=on_action,
            data={"count": 0}
        )

        await utils.answer(
            mx, 
            self.strings["actions"].format(count=0), 
            event=event, 
            reply_markup=markup
        )
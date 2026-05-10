#			__  ____  ___   _               _           _   
#			|  \/  \ \/ / | | |___  ___ _ __| |__   ___ | |_ 
#			| |\/| |\  /| | | / __|/ _ \ '__| '_ \ / _ \| __|
#			| |  | |/  \| |_| \__ \  __/ |  | |_) | (_) | |_ 
#			|_|  |_/_/\_\\___/|___/\___|_|  |_.__/ \___/ \__| 
#
# 🔒      Licensed under the GNU AGPLv3
# 🌐 https://www.gnu.org/licenses/agpl-3.0.html


class Meta:
    name = "RolePlay"
    description = "RP actions via .rp"
    version = "2.0.0"
    tags = ["roleplay", "fun"]


from mxc import utils
from .. import loader


MANAGEMENT_CMDS = {"add", "new", "remove", "rm", "del", "delete", "list"}


class RolePlayStore:
    DEFAULT_ACTIONS = {
        "hug": {"verb": "hugged 🤗", "needs_confirm": True},
        "slap": {"verb": "slapped 🖐️", "needs_confirm": False},
        "kiss": {"verb": "kissed 💋", "needs_confirm": True},
        "cuddle": {"verb": "cuddled 🥰", "needs_confirm": False},
        "pat": {"verb": "patted 👋", "needs_confirm": False},
        "poke": {"verb": "poked 👉", "needs_confirm": False},
        "обнять": {"verb": "обнял 🤗", "needs_confirm": False},
        "пинок": {"verb": "пнул 👞", "needs_confirm": False},
        "поцеловать": {"verb": "поцеловал 💋", "needs_confirm": True},
    }

    def __init__(self, get_fn, set_fn):
        self._get = get_fn
        self._set = set_fn

    async def load(self):
        actions = await self._get("actions", None)
        if actions is None:
            actions = dict(self.DEFAULT_ACTIONS)
            await self._set("actions", actions)
        return actions

    async def add(self, actions, name, verb=None, needs_confirm=False):
        name = name.lower().strip()
        if not name:
            return False, "empty_name"
        if name in actions:
            return False, "exists"
        if name in MANAGEMENT_CMDS:
            return False, "reserved"
        actions[name] = {"verb": verb or name, "needs_confirm": needs_confirm}
        await self._set("actions", actions)
        return True, "added"

    async def remove(self, actions, name):
        name = name.lower().strip()
        if name in self.DEFAULT_ACTIONS:
            return False, "default"
        if name not in actions:
            return False, "not_found"
        del actions[name]
        await self._set("actions", actions)
        return True, "removed"


@loader.tds
class RolePlayModule(loader.Module):
    strings = {
        "action_msg": "<b>{sender}</b> {verb} <b>{target}</b>",
        "confirm_title": "<b>{sender}</b> wants to {verb} <b>{target}</b> 🤔",
        "confirmed": "<b>{sender}</b> {verb} <b>{target}</b> 💕",
        "cancelled": "❌ Cancelled",
        "need_target": "❌ Reply to someone or mention a user",
        "access_denied": "❌ You don't have access to this module",
        "add_access_denied": "❌ You don't have access to add RP commands",
        "exists": "❌ Action <code>{name}</code> already exists",
        "added": "✅ Action <code>{name}</code> added",
        "not_found": "❌ Action <code>{name}</code> not found",
        "removed": "✅ Action <code>{name}</code> removed",
        "cannot_remove_default": "❌ Cannot remove default action <code>{name}</code>",
        "list_title": "📋 <b>Available RP actions:</b>\n",
        "list_item": "• <code>{prefix}rp {name}</code> {note}\n",
        "empty_name": "❌ Action name cannot be empty",
        "reserved": "❌ <code>{name}</code> is a reserved management command name",
        "no_such_action": "❌ Unknown action <code>{name}</code>",
        "usage": '❌ Usage:\n<code>{prefix}rp &lt;action&gt; [@user]</code>\n<code>{prefix}rp add &lt;action&gt;</code>\n<code>{prefix}rp add request &lt;action&gt;</code>\n<code>{prefix}rp remove &lt;action&gt;</code>\n<code>{prefix}rp list</code>',
    }

    config = {
        "access": loader.ConfigValue(
            "all",
            "Who can use RP: all, sudo, owner, or comma-separated mxid list"
        ),
        "add_access": loader.ConfigValue(
            "all",
            "Who can add RP commands: all, sudo, owner, or comma-separated mxid list"
        ),
    }

    def __init__(self):
        self.store = None
        self._actions = {}

    async def _matrix_start(self, mx):
        self.store = RolePlayStore(self._get, self._set)
        self._actions = await self.store.load()

    def _has_access(self, mx, sender, access_type="access"):
        conf = self.config.get(access_type, "all").strip().lower()
        if conf == "all":
            return True
        if conf == "owner":
            return mx.security.is_owner(sender)
        if conf == "sudo":
            return sender in mx.security.sudos or mx.security.is_owner(sender)
        allowed = [x.strip() for x in conf.replace("\n", ",").split(",") if x.strip()]
        if sender in allowed:
            return True
        perms = mx.security.mod_perms.get(sender, [])
        if self.__class__.__name__.lower() in perms:
            return True
        return False

    async def _get_target(self, mx, event, args):
        reply = await utils.get_reply_event(mx, event)
        if reply:
            return reply.sender
        if args:
            return args.strip()
        return None

    @loader.command(aliases=["rp", "рп"], security=loader.ALL)
    async def rp(self, mx, event):
        """<action> [@user] / add / add request / remove / list"""
        print(1)
        if not self._has_access(mx, event.sender, "access"):
            await utils.answer(mx, self.strings.get("access_denied"), event=event)
            return

        prefix = await utils.get_prefix(mx)
        raw = await utils.get_args_raw(mx, event)

        if not raw:
            await utils.answer(mx, self.strings.get("usage").format(prefix=prefix), event=event)
            return

        parts = raw.split(maxsplit=2)
        subcmd = parts[0].lower().strip("\"'")

        if subcmd == "list":
            await self._cmd_list(mx, event, prefix)

        elif subcmd in ("add", "new"):
            await self._cmd_add(mx, event, prefix, parts)

        elif subcmd in ("remove", "rm", "del", "delete"):
            await self._cmd_remove(mx, event, prefix, parts)

        elif subcmd in self._actions:
            await self._exec_action(mx, event, subcmd, parts)

        else:
            await utils.answer(mx, self.strings.get("no_such_action").format(name=subcmd), event=event)

    async def _cmd_list(self, mx, event, prefix):
        text = self.strings.get("list_title")
        for name, act in self._actions.items():
            note = "(request)" if act.get("needs_confirm") else ""
            text += self.strings.get("list_item").format(prefix=prefix, name=name, note=note)
        await utils.answer(mx, text.strip(), event=event)

    async def _cmd_add(self, mx, event, prefix, parts):
        if not self._has_access(mx, event.sender, "add_access"):
            await utils.answer(mx, self.strings.get("add_access_denied"), event=event)
            return

        needs_confirm = False
        if len(parts) >= 3 and parts[1].lower() == "request":
            needs_confirm = True
            action_name = parts[2].strip().lower().strip("\"'")
        elif len(parts) >= 2:
            action_name = parts[1].strip().lower().strip("\"'")
        else:
            action_name = ""

        if not action_name:
            await utils.answer(mx, self.strings.get("empty_name"), event=event)
            return

        ok, key = await self.store.add(self._actions, action_name, needs_confirm=needs_confirm)
        await utils.answer(mx, self.strings.get(key).format(name=action_name), event=event)

    async def _cmd_remove(self, mx, event, prefix, parts):
        if not self._has_access(mx, event.sender, "add_access"):
            await utils.answer(mx, self.strings.get("add_access_denied"), event=event)
            return

        action_name = parts[1].strip().lower().strip("\"'") if len(parts) >= 2 else ""
        if not action_name:
            await utils.answer(mx, self.strings.get("empty_name"), event=event)
            return

        ok, key = await self.store.remove(self._actions, action_name)
        if not ok and key == "default":
            key = "cannot_remove_default"
        await utils.answer(mx, self.strings.get(key).format(name=action_name), event=event)

    async def _exec_action(self, mx, event, action_name, parts):
        action = self._actions[action_name]
        args = parts[1].strip() if len(parts) > 1 else ""

        target = await self._get_target(mx, event, args)
        if not target:
            await utils.answer(mx, self.strings.get("need_target"), event=event)
            return

        sender = event.sender

        if action.get("needs_confirm"):
            async def on_confirm(ctx):
                if ctx.payload == "yes":
                    await ctx.edit(
                        self.strings.get("confirmed").format(
                            sender=sender, verb=action["verb"], target=target
                        )
                    )
                else:
                    await ctx.edit(self.strings.get("cancelled"))
                await ctx.close(clear_reactions=True)

            allowed = [sender]
            if target.startswith("@"):
                allowed.append(target)

            markup = utils.EmojiKeyBoard(
                rows=[[
                    utils.EmojiButton("✅", "yes"),
                    utils.EmojiButton("❌", "no"),
                ]],
                callback=on_confirm,
                allowed_senders=allowed,
                single_use=True,
            )

            await utils.answer(
                mx,
                self.strings.get("confirm_title").format(
                    sender=sender, verb=action["verb"], target=target
                ),
                event=event,
                reply_markup=markup,
            )
        else:
            await utils.answer(
                mx,
                self.strings.get("action_msg").format(
                    sender=sender, verb=action["verb"], target=target
                ),
                event=event,
            )

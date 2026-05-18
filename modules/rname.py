from .. import loader
from mxc import utils


class Meta:
    name = "RoomName"
    description = "Change display name per room"
    version = "1.1.0"
    tags = ["utility"]


@loader.tds
class RoomNameModule(loader.Module):
    strings = {
        "set_room_nick_succ": "<b>✅ | Name changed to</b> <code>{name}</code>",
        "reset_name": "<b>✅ | Reset to global name:</b> <code>{displayname}</code>"
    }


    @loader.command()
    async def setname(
        self,
        mx,
        event,
        name: str
    ):
        """<name> - Set your display name in this room"""
        await utils.set_room_nick(
            mx,
            event.room_id,
            name
        )
        await utils.answer(
            mx,
            self.strings.get(
                "set_room_nick_succ"
            ).format(
                name=name
            )
        )


    @loader.command()
    async def resetname(
        self,
        mx,
        event
    ):
        """Reset to global display name in this room"""
        profile = await utils.get_profile(
            mx,
            mx.client.mxid
        )
        await utils.set_room_nick(
            mx,
            event.room_id,
            profile.displayname
        )

        await utils.answer(
            mx,
            self.strings.get(
                "reset_name"
            ).format(
                displayname=profile.displayname
            )
        )

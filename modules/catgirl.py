#			__  ____  ___   _               _           _   
#			|  \/  \ \/ / | | |___  ___ _ __| |__   ___ | |_ 
#			| |\/| |\  /| | | / __|/ _ \ '__| '_ \ / _ \| __|
#			| |  | |/  \| |_| \__ \  __/ |  | |_) | (_) | |_ 
#			|_|  |_/_/\_\\___/|___/\___|_|  |_.__/ \___/ \__| 
#
# 🔒      Licensed under the GNU AGPLv3
# 🌐 https://www.gnu.org/licenses/agpl-3.0.html


class Meta:
    name = "CatGirl"
    description = "via Nekosia API."
    version = "2.0.0"
    author = "https://github.com/PashaHatsune"
    tags = ["api", "media"]


from mxc import utils
from mxc.exceptions import UsageError
from mxc.types import EmojiButton, Image
from mxc.utils.keyboard import EmojiKeyBoard
from .. import loader


@loader.tds
class CatGirlModule(loader.Module):
    strings = {
        "fetching": "🐱 | <b>Locating a tactical catgirl...</b>",
        "error": "❌ | <b>API failure:</b> <code>{err}</code>",
        "caption": "✨ | <b>Catgirl ID:</b> <code>{id}</code>"
    }

    @loader.command()
    async def catgirl(
        self,
        mx,
        event
    ):
        """Summon a random catgirl picture"""
        ids = await utils.answer(mx, self.strings.get("fetching"))

        api_url = "https://api.nekosia.cat/api/v1/images/catgirl"

        try:
            data = await utils.request(api_url)
            
            img_url = data["image"]["original"]["url"]
            img_id = data["id"]

            async def on_reload(ctx):
                try:
                    new_data = await utils.request(api_url)
                    new_url = new_data["image"]["original"]["url"]
                    new_id = new_data["id"]

                    markup = EmojiKeyBoard(
                        rows=[[EmojiButton(emoji="🔄", data="reload")]],
                        callback=on_reload
                    )

                    await ctx.close()
                    await utils.answer(
                        ctx.mx,
                        media=Image(
                            url=new_url,
                            caption=self.strings.get("caption").format(id=new_id)
                        ),
                        edit_id=ctx.message_id,
                        reply_markup=markup,
                    )
                except Exception:
                    pass

            markup = EmojiKeyBoard(
                rows=[[EmojiButton(emoji="🔄", data="reload")]],
                callback=on_reload,
                remove_clicked=False,
            )

            await utils.answer(
                mx,
                media=Image(
                    url=img_url,
                    caption=self.strings.get("caption").format(id=img_id)
                ),
                edit_id=ids,
                reply_markup=markup,
            )

        except (TypeError, KeyError, IndexError):
            raise UsageError()
        except Exception as e:
            raise e
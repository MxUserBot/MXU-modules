#			__  ____  ___   _               _           _   
#			|  \/  \ \/ / | | |___  ___ _ __| |__   ___ | |_ 
#			| |\/| |\  /| | | / __|/ _ \ '__| '_ \ / _ \| __|
#			| |  | |/  \| |_| \__ \  __/ |  | |_) | (_) | |_ 
#			|_|  |_/_/\_\\___/|___/\___|_|  |_.__/ \___/ \__| 
#
# 🔒      Licensed under the GNU AGPLv3
# 🌐 https://www.gnu.org/licenses/agpl-3.0.html


class Meta:
    name = "Astolfo"
    description = "Astolfo pic from astolfo.rocks."
    version = "2.0.0"
    tags = ["api", "media"]


from mxc import utils
from mxc.types import EmojiButton, Image
from mxc.utils.keyboard import EmojiKeyBoard
from .. import loader


@loader.tds
class AstolfoModule(loader.Module):
    strings = {
        "fetching": "🌸 | <b>Summoning a wild Astolfo...</b>",
        "error": "❌ | <b>Deployment failure:</b> <code>{err}</code>",
        "caption": "✨ | <b>Asset ID:</b> <code>{id}</code> | <b>Rating:</b> <code>{rating}</code>"
    }


    @loader.command()
    async def astolfo(
        self,
        mx,
        event,
        rating: str = "safe"
    ):
        """<rating> - Summon a random Astolfo picture"""

        ids = await utils.answer(mx, self.strings.get("fetching"))

        api_url = "https://astolfo.rocks/api/images/random"

        try:
            data = await utils.request(api_url, params={"rating": rating.lower()})
            
            img_id = data["id"]
            ext = data["file_extension"]
            img_url = f"https://astolfo.rocks/astolfo/{img_id}.{ext}"

            async def on_reload(ctx):
                try:
                    new_data = await utils.request(api_url, params={"rating": rating.lower()})
                    new_id = new_data["id"]
                    new_ext = new_data["file_extension"]
                    new_url = f"https://astolfo.rocks/astolfo/{new_id}.{new_ext}"

                    markup = EmojiKeyBoard(
                        rows=[[EmojiButton(emoji="🔄", data="reload")]],
                        callback=on_reload
                    )

                    await ctx.close()
                    await utils.answer(
                        ctx.mx,
                        media=Image(
                            url=new_url,
                            caption=self.strings.get("caption").format(id=new_id, rating=rating),
                            filename="astolfo.png",
                            mimetype="image/png"
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
                    caption=self.strings.get("caption").format(id=img_id, rating=rating),
                    filename="astolfo.png",
                    mimetype="image/png"
                ),
                edit_id=ids,
                reply_markup=markup,
            )

        except Exception as e:
            raise e

from discord.ext import commands
from ...dbhandler import DBHandler

base_sheet_url = 'https://docs.google.com/spreadsheets/d/'


def write_property(server_id, key, value):
    """ Update a single property of a server's config """
    with DBHandler() as handler:
        handler.update_server_config(server_id, key, value)


def start_check(arg_check, arg_fail):
    def start_decorator(func):
        async def func_wrapper(ctx, arg):
            if arg.startswith(arg_check):
                await ctx.send(arg_fail)
            else:
                await func()
        return func_wrapper
    return start_decorator


class Config:
    def __init__(self, bot):
        self.bot = bot

    @start_check(base_sheet_url, "Invalid spreadsheet link.")
    @commands.command(pass_context=True)
    async def set_sheet(self, ctx, url):
        # cut the stuff surrounding the key
        doc_key = url[len(base_sheet_url):]
        doc_key = doc_key[:doc_key.find('/')]

        write_property('doc_key', doc_key)

        server_info = self.bot.server_info[ctx.guild.id]
        await server_info.update()


def setup(bot):
    bot.add_cog(Config(bot))

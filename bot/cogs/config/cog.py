from discord.ext import commands
from ...dbhandler import DBHandler


class Config(commands.Converter):
    def __init__(self, bot):
        self.bot = bot


def setup(bot):
    bot.add_cog(Config(bot))

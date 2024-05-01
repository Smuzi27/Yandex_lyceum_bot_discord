import discord
import logging
import json
import requests
import asyncio
from discord.ext import commands

API_KEY = "828a9ce4eea04372be2a390a662c63be"

try:
    with open("bad_words.txt", "r", encoding="utf-8") as f:
        profanity_list = f.read().splitlines()
except FileNotFoundError:
    profanity_list = []

TOKEN = 'MTIzNDg2NTI4NjYwNDM5MDQ3MQ.GgTNv9.SGNKsjleJPvRq4TFcGpx9YZ66mogd5-22yiwog'

logger = logging.getLogger('discord')
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)

HELP_TEXT = """
Вы используете бота модератора созданного в рамках проекта яндекс лицей.
Он умеет вычислять плохие слова и выдавать предупреждения и банны пользователям и выводить курс валют.
!help - вызов сообщения с помощью пользователю;
!abso(!absolution) - Обнуление количества нарушений у пользователя. Пример: !abso user_123;
!prof_list(!profanity_list) - Список плохих слов;
!add_prof(!add_profanity) - Добавление в список плохого слова. Пример: !add_prof банан;
!del_prof(!del_profanity) - Удаление запретного слова. Пример: !del_prof банан;
!curr(!currency) - Вывод курса валют. Пример: !curr EUR-RUB
"""


class MyHelpCommand(commands.MinimalHelpCommand):
    async def send_pages(self):
        destination = self.get_destination()
        e = discord.Embed(color=discord.Color.dark_red(), description='')
        e.description += HELP_TEXT
        await destination.send(embed=e)


intents = discord.Intents.default()
intents.members = True
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents, help_command=MyHelpCommand())


class ProfanityMod(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.profanity_list = profanity_list
        self.infractions = {}
        self.last_message_time = {}
        self.flag = True

        try:
            with open("infractions.json", "r") as file:
                self.infractions = json.load(file)
        except FileNotFoundError:
            pass

    async def check_profanity(self, message):
        content = message.content.lower()
        if self.flag:
            for word in self.profanity_list:
                if word in content:
                    author_id = str(message.author.id)
                    if author_id not in self.infractions:
                        self.infractions[author_id] = 1
                    else:
                        self.infractions[author_id] += 1
                    if self.infractions[author_id] >= 5:
                        guild = message.guild
                        await guild.ban(message.author, reason="Repeated use of profanity")
                        await message.channel.send(
                            f"{message.author.mention} has been banned for repeated use of profanity.")
                        self.infractions[author_id] = 0
                    else:
                        await message.channel.send(
                            f"{message.author.mention}, watch your language! This is a warning. Infraction count: {self.infractions[author_id]}")

                    with open("infractions.json", "w") as file:
                        json.dump(self.infractions, file)

    @commands.Cog.listener()
    async def on_message(self, message):
        if not message.author.bot:
            await self.check_profanity(message)

    @commands.command(name="absolution", aliases=["abso"], help="Обнуление количества нарушений у пользователя")
    async def thank(self, ctx, user: discord.User):
        if ctx.message.author.guild_permissions.administrator:
            user_id = str(user.id)
            if user_id in self.infractions:
                self.infractions[user_id] = 0
                await ctx.send(f"Infraction count reset for {user.mention}.")
            else:
                await ctx.send("User has no infractions.")
        else:
            await ctx.send("You do not have sufficient permissions to use this command.")

        with open("infractions.json", "w") as file:
            json.dump(self.infractions, file)

    @commands.command(name="profanity_list", aliases=["prof_list"])
    async def profanity_list(self, ctx):
        await ctx.send("Список плохих слов:")
        await ctx.send(" ,".join(self.profanity_list))

    @commands.command(name="add_profanity", aliases=["add_prof"])
    async def add_profanity(self, ctx, word: str):
        self.flag = False
        if ctx.message.author.guild_permissions.administrator:
            if word in self.profanity_list:
                await ctx.send(f"Плохое слово `{word}` уже добавлено в список.")
            else:
                self.profanity_list.append(word)
                await ctx.send(f"Плохое слово `{word}` успешно добавлено в список.")
                with open("bad_words.txt", "w", encoding="utf-8") as f:
                    f.write('\n'.join(profanity_list))
        self.flag = True

    @commands.command(name="del_profanity", aliases=["del_prof"])
    async def del_profanity(self, ctx, word: str):
        self.flag = False
        if ctx.message.author.guild_permissions.administrator:
            if word in self.profanity_list:
                self.profanity_list.remove(word)
                with open("bad_words.txt", "w", encoding="utf-8") as f:
                    f.write('\n'.join(profanity_list))
                await ctx.send(f"Плохое слово `{word}` успешно удалено из списка.")
        else:
            await ctx.send(f"Плохое слово `{word}` не найдено в списке.")
        self.flag = True

    def get_currency(self):
        response = requests.get(self.currency_api_url)
        if response.status_code == 200:
            data = response.json()
            return data
        else:
            return 'Произошла ошибка при загрузке курса валют.'

    @commands.command(name="currency", aliases=["curr"])
    async def profanity_list(self, ctx, options):
        self.api_key = API_KEY
        self.currency_api_url = f'https://openexchangerates.org/api/latest.json?app_id={self.api_key}'
        currencies = options.split("-")
        print(currencies)
        if len(currencies) != 2:
            await ctx.channel.send("Пожалуйста, укажите две валюты для получения их курса. В формате EUR-RUB")
        base_currency, target_currency = currencies
        currency_data = self.get_currency()
        if base_currency.upper() not in currency_data['rates'] or target_currency.upper() not in currency_data[
            'rates']:
            await ctx.channel.send("Неверные коды валют. Пожалуйста, укажите корректные коды валют.")
        base_rate = currency_data['rates'][base_currency.upper()]
        target_rate = currency_data['rates'][target_currency.upper()]
        await ctx.channel.send(
            f"Курс {base_currency.upper()} к {target_currency.upper()}: {target_rate / base_rate:.2f}")


@bot.event
async def on_ready():
    print('Bot is ready.')


async def main():
    await bot.add_cog(ProfanityMod(bot))
    await bot.start(TOKEN)


asyncio.run(main())

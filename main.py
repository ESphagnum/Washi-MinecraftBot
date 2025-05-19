import discord
from discord.ext import commands
import os
import config
from Modules.Tools.main import *
import aiohttp
from io import BytesIO
import config
import logging


# Создание экземпляра бота
bot = commands.Bot(command_prefix="!", intents=discord.Intents.all())

logging.basicConfig(level=logging.DEBUG, filename="logs.xml", filemode="w")

@bot.event
async def on_ready():
    """Событие запуска бота."""
    print(f"Бот {bot.user} запущен!")
    logging.debug(f"Bot {bot.user} is running!")
    
    await load_cogs()
    try:
        synced = await bot.tree.sync()
        print(f"Синхронизировано {len(synced)} команд: {synced}")
    except Exception as e:
        print(f"Ошибка синхронизации команд: {e}")


async def load_cogs():
    """Функция загрузки всех модулей (cogs)."""
    print("Загружаем модули...")
    logging.debug("Loading modules...")

    loaded_cogs = []
    failed_cogs = []

    for folder in os.listdir("./Modules"):
        cog_path = f"Modules.{folder}.main"
        if os.path.exists(f"./Modules/{folder}/main.py"):
            try:
                await bot.load_extension(cog_path)
                loaded_cogs.append(folder)
            except Exception as e:
                failed_cogs.append((folder, str(e)))

    print(f"Загруженные модули: {', '.join(loaded_cogs) if loaded_cogs else 'Нет'}")
    logging.info(f"Загруженные модули: {', '.join(loaded_cogs) if loaded_cogs else 'Нет'}")

    if failed_cogs:
        print("Не удалось загрузить следующие модули:")
        logging.critical("Не удалось загрузить следующие модули:")
        for cog, error in failed_cogs:
            print(f"- {cog}: {error}")
            logging.critical(f"- {cog}: {error}")


async def unload_cogs():
    """Функция выгрузки всех модулей (cogs)."""
    print("Выгружаем модули...")
    logging.debug("Выгружаем модули...")

    unloaded_cogs = []
    failed_cogs = []

    for folder in os.listdir("./Modules"):
        cog_path = f"Modules.{folder}.main"
        if os.path.exists(f"./Modules/{folder}/main.py"):
            try:
                await bot.unload_extension(cog_path)
                unloaded_cogs.append(folder)
            except Exception as e:
                failed_cogs.append((folder, str(e)))

    print(f"Выгруженные модули: {', '.join(unloaded_cogs) if unloaded_cogs else 'Нет'}")
    logging.info(f"Выгруженные модули: {', '.join(unloaded_cogs) if unloaded_cogs else 'Нет'}")
    if failed_cogs:
        print("Модули с ошибкой:")
        logging.critical("Модули с ошибкой:")
        for cog, error in failed_cogs:
            print(f"- {cog}: {error}")
            logging.critical(f"- {cog}: {error}")


@bot.command(name="reload", description="Перезагружает все модули бота")
@commands.has_role(config.SETTINGS["command_role"])
async def reload(interaction: discord.Interaction):
    """Команда для перезагрузки всех модулей."""
    await interaction.response.send_message("Перезагрузка модулей...")
    await unload_cogs()
    await load_cogs()
    await interaction.followup.send("Модули перезагружены!")


@bot.command(aliases=['dev'], description="Dev Info")
async def developer(ctx):
    await Tools.respond(ctx, embed=discord.Embed(title=config.LANG["name"])
    .add_field(name=config.LANG["author"], value="<@1061998983158964285>")
    .add_field(name=config.LANG["Discord"], value=config.LANG["Discord_link"])
    .add_field(name=config.LANG["Main_Language"], value="Eng")
    .set_thumbnail(url="https://images.wallpaperscraft.ru/image/single/mem_dovolnyj_litso_64470_1600x1200.jpg"))


@bot.command(name="developer2", description="Информация о разработчике")
async def developer_slash(interaction: discord.Interaction):
    await interaction.response.send_message(embed=discord.Embed(title=config.LANG["name"])
    .add_field(name=config.LANG["author"], value="<@1061998983158964285>")
    .add_field(name=config.LANG["Discord"], value=config.LANG["Discord_link"])
    .add_field(name=config.LANG["Main_Language"], value="Eng")
    .set_thumbnail(url="https://images.wallpaperscraft.ru/image/single/mem_dovolnyj_litso_64470_1600x1200.jpg"))


@bot.event
async def on_command_error(ctx: commands.Context, error: commands.CommandError):
    """Обработчик ошибок команд."""
    if isinstance(error, commands.MissingRole):
        await Tools.respond(ctx, embed=discord.Embed(title="Error").add_field(name="У вас нет роли, необходимой для выполнения этой команды.", value=" "))
    elif isinstance(error, commands.MissingAnyRole):
        await Tools.respond(ctx, embed=discord.Embed(title="Error").add_field(name="Вам не хватает одной из необходимых ролей для выполнения этой команды.", value=" "))
    elif isinstance(error, commands.CommandNotFound):
        await Tools.respond(ctx, embed=discord.Embed(title="Error").add_field(name="Команда не найдена.", value=" "))
    elif isinstance(error, commands.CommandOnCooldown):
        await Tools.respond(ctx, embed=discord.Embed(title="Error").add_field(name=f"Команда на перезарядке. Подождите {round(error.retry_after, 2)} секунд.", value=" "))
    else:
        await Tools.respond(ctx, embed=discord.Embed(title="Error").add_field(name="Хз чё за ошибка", value=error))
        print(error)
        logging.error(error)


@bot.command(name="add_emojigg", description="Добавляет эмодзи с emoji.gg")
async def add_emojigg(interaction: discord.Interaction, arg: str):
    try:
        # Разбираем аргументы команды
        parts = arg.split()
        if len(parts) != 2 or not parts[0].startswith("type:") or not parts[1].startswith("id:"):
            return await interaction.response.send_message("Используйте формат: /add_emojigg type:emoji id:XXXX-name")
        
        emoji_id = parts[1][3:].split('-')[0]  # Получаем ID эмодзи
        
        async with aiohttp.ClientSession() as session:
            async with session.get("https://emoji.gg/api/") as response:
                if response.status != 200:
                    return await interaction.response.send_message("Не удалось получить список эмодзи.")
                
                data = await response.json()
                
                # Ищем эмодзи по ID
                emoji_data = next((e for e in data if str(e['id']) == emoji_id), None)
                if not emoji_data:
                    return await interaction.response.send_message("Эмодзи с таким ID не найдено.")
                
                emoji_url = emoji_data['image']
                emoji_name = emoji_data['slug']
                
                # Загружаем эмодзи на сервер
                async with session.get(emoji_url) as img_response:
                    if img_response.status != 200:
                        return await interaction.response.send_message("Ошибка загрузки изображения эмодзи.")
                    img_data = BytesIO(await img_response.read()).getvalue()
                    
                    guild = interaction.guild
                    is_animated = emoji_url.endswith(".gif")
                    emoji = await guild.create_custom_emoji(name=emoji_name, image=img_data, animated=is_animated)
                    
                    await interaction.response.send_message(f'✅ Эмодзи {emoji.name} добавлено! {emoji}')
    
    except discord.HTTPException:
        await interaction.response.send_message("❌ Ошибка: файл слишком большой!")
    except Exception as e:
        await interaction.response.send_message(f'❌ Ошибка: {e}')


@bot.command(name="add_emoji", description="Добавляет эмодзи по ссылке")
async def add_emoji(interaction: discord.Interaction, url: str, name: str):
    if not interaction.user.guild_permissions.manage_emojis:
        return await interaction.response.send_message("❌ У вас нет прав на управление эмодзи!", ephemeral=True)
    
    try:
        async with aiohttp.ClientSession() as ses:
            async with ses.get(url) as r:
                if r.status not in range(200, 299):
                    return await interaction.response.send_message(f'Ошибка при запросе | Код ответа: {r.status}.')
                
                try:
                    img_or_gif = BytesIO(await r.read())
                    b_value = img_or_gif.getvalue()
                    emoji = await interaction.guild.create_custom_emoji(image=b_value, name=name)
                    await interaction.response.send_message(f'Успешно создано эмодзи: <:{name}:{emoji.id}>')
                except discord.HTTPException:
                    await interaction.response.send_message('❌ Размер файла слишком большой!')
                except Exception as e:
                    await interaction.response.send_message(f'❌ Ошибка: {e}')
    except Exception as e:
        await interaction.response.send_message(f'❌ Ошибка: {e}')


@bot.command(name="delete_emoji", description="Удаляет эмодзи")
async def delete_emoji(interaction: discord.Interaction, emoji: discord.Emoji):
    if not interaction.user.guild_permissions.manage_emojis:
        return await interaction.response.send_message("❌ У вас нет прав на управление эмодзи!", ephemeral=True)
    
    try:
        await emoji.delete()
        await interaction.response.send_message(f'✅ Эмодзи {emoji.name} удалено!')
    except Exception as e:
        await interaction.response.send_message(f'❌ Ошибка при удалении: {e}')


if __name__ == "__main__":
    try:
        bot.run(config.SETTINGS["TOKEN"])
    except Exception as e:
        print(f"Не удалось запустить бота: {e}")
        logging.critical(f"Не удалось запустить бота: {e}")
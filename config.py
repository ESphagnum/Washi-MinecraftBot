import os

# Main config.py
language = os.getenv('Lang')

SETTINGS = {
    "command_role": 1061998983158964285,
    "hasntRole_embed_color": 0xff1100,
    "GUILD": os.getenv('Guild'),
    "TOKEN": os.getenv('BOT_TOKEN')
}
LANG = {
    "name": "Discord SukaBot 3000",
    "author": "Author",
    "Discord": "Discord",
    "Discord_link": "[Link](https://discord.gg/XTe6D8czUs)",
    "Main_Language": "Main Language",
    "role": {
        "hasntRole_title": "ERROR",
        "hasntRole_description": ":flag_ru: **RU**\nУ вас нет доступа!\n\n:flag_us: **EN**\nYou don't have access!"
    }
}

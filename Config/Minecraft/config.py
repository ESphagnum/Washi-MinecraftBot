import json
from config import language

useEmbed = False
locate = f"Lang/Minecraft/minecraft_{language}.json"
loc = json.load(open(locate,"r",encoding="utf-8"))
save_path = "Saves/Minecraft/data.json"
allowed_role_ids = ["id"]
import discord
from discord.ext import commands, tasks
from discord import app_commands
from mcstatus import JavaServer, BedrockServer
from mcrcon import MCRcon
from Config.Minecraft.config import *
import json
import os
import asyncio
from typing import Optional, Literal

class Minecraft(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.server_info = {}
        self.data_file = save_path
        self.load_data()
        self.update_embed.start()
        self.update_status.start()

    def cog_unload(self):
        self.update_embed.cancel()
        self.update_status.cancel()
        self.save_data()

    def load_data(self):
        if os.path.exists(self.data_file):
            with open(self.data_file, 'r') as f:
                data = json.load(f)
                self.server_info = {int(k): v for k, v in data.items()}
        else:
            self.server_info = {}

    def save_data(self):
        with open(self.data_file, 'w') as f:
            json.dump(self.server_info, f, indent=4)

    async def get_server_status(self, server_type: str, address: str):
        try:
            if server_type == "java":
                server = JavaServer.lookup(address)
                status = server.status()
                return {
                    "online": True,
                    "players": status.players.online,
                    "max_players": status.players.max,
                    "player_list": [player.name for player in status.players.sample] if hasattr(status.players, 'sample') and status.players.sample else [],
                    "version": status.version.name,
                    "latency": status.latency
                }
            elif server_type == "bedrock":
                server = BedrockServer.lookup(address)
                status = server.status()
                return {
                    "online": True,
                    "players": status.players_online,
                    "max_players": status.players_max,
                    "player_list": [],
                    "version": status.version.version,
                    "latency": status.latency
                }
        except Exception:
            return {"online": False}

    async def execute_rcon(self, channel_id: int, command: str):
        if channel_id not in self.server_info:
            return None
        
        server_data = self.server_info[channel_id]
        if "rcon" not in server_data or not server_data["rcon"].get("enabled", False):
            return None
        
        try:
            with MCRcon(
                server_data["address"].split(":")[0],
                server_data["rcon"]["password"],
                port=server_data["rcon"].get("port", 25575)
            ) as mcr:
                return mcr.command(command)
        except Exception as e:
            print(f"RCON error: {e}")
            return None

    @app_commands.command(name="add_server", description="Добавить новый сервер для отслеживания")
    @app_commands.describe(
        channel="Канал для отображения статуса",
        address="Адрес сервера (host:port)",
        server_type="Тип сервера",
        show_players="Показывать список игроков",
        show_in_status="Показывать в статусе бота",
        display_in_status="Что показывать в статусе бота"
    )
    async def add_server(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel,
        address: str,
        server_type: Literal["java", "bedrock"] = "java",
        show_players: bool = True,
        show_in_status: bool = False,
        display_in_status: Literal["players", "ip"] = "players"
    ):
        if not any(role.id in allowed_role_ids for role in interaction.user.roles):
            embed = discord.Embed(
                title="Ошибка",
                description="У вас недостаточно прав для выполнения этой команды.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        if channel.id in self.server_info:
            embed = discord.Embed(
                title="Ошибка",
                description="Этот канал уже привязан к серверу.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        if ":" in address:
            host, port = address.split(":")
            try:
                port = int(port)
            except ValueError:
                embed = discord.Embed(
                    title="Ошибка",
                    description="Неверный формат порта в адресе сервера.",
                    color=discord.Color.red()
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
        else:
            address = f"{address}:25565" if server_type == "java" else f"{address}:19132"

        self.server_info[channel.id] = {
            "address": address,
            "type": server_type,
            "players": show_players,
            "message": None,
            "last_status": "unknown",
            "show_in_status": show_in_status,
            "display_in_status": display_in_status,
            "rename_channel": True,
            "rcon": {"enabled": False}
        }

        self.save_data()

        embed = discord.Embed(
            title=f"Сервер {address}",
            description="Получение информации о сервере...",
            color=discord.Color.orange()
        )
        message = await channel.send(embed=embed)
        self.server_info[channel.id]["message"] = message.id
        self.save_data()

        await self.update_server_embed(channel)

        embed = discord.Embed(
            title="Сервер добавлен",
            description=f"Сервер {address} ({server_type}) успешно добавлен в канал {channel.mention}.",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)


    @app_commands.command(name="command", description="Выполнить команду на сервере")
    @app_commands.describe(command="Команда для выполнения (без /)")
    async def server_command(self, interaction: discord.Interaction, command: str):
        if not any(role.id in allowed_role_ids for role in interaction.user.roles):
            embed = discord.Embed(
                title="Ошибка",
                description="У вас недостаточно прав для выполнения этой команды.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        if interaction.channel.id not in self.server_info:
            embed = discord.Embed(
                title="Ошибка",
                description="Этот канал не привязан к серверу.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        server_data = self.server_info[interaction.channel.id]
        if "rcon" not in server_data or not server_data["rcon"].get("enabled", False):
            embed = discord.Embed(
                title="Ошибка",
                description="RCON не настроен для этого сервера.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        embed = discord.Embed(
            title="Команда отправлена",
            description=f"Команда `{command}` отправлена на сервер.",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

        result = await self.execute_rcon(interaction.channel.id, command)
        
        if "rcon" in server_data and server_data["rcon"].get("log_channel"):
            log_channel = self.bot.get_channel(server_data["rcon"]["log_channel"])
            if log_channel:
                log_embed = discord.Embed(
                    title="Выполнена RCON команда",
                    color=discord.Color.blue()
                )
                log_embed.add_field(name="Сервер", value=server_data["address"], inline=False)
                log_embed.add_field(name="Пользователь", value=interaction.user.mention, inline=False)
                log_embed.add_field(name="Команда", value=f"`/{command}`", inline=False)
                if result:
                    log_embed.add_field(name="Результат", value=f"```{result[:1000]}```", inline=False)
                await log_channel.send(embed=log_embed)

    @app_commands.command(name="server_list", description="Показать список всех отслеживаемых серверов")
    async def server_list(self, interaction: discord.Interaction):
        if not any(role.id in allowed_role_ids for role in interaction.user.roles):
            embed = discord.Embed(
                title="Ошибка",
                description="У вас недостаточно прав для выполнения этой команды.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        if not self.server_info:
            embed = discord.Embed(
                title="Список серверов",
                description="Нет отслеживаемых серверов.",
                color=discord.Color.blue()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        embed = discord.Embed(
            title="Список отслеживаемых серверов",
            color=discord.Color.blue()
        )

        for channel_id, server_data in self.server_info.items():
            channel = self.bot.get_channel(channel_id)
            channel_name = f"Удалённый канал ({channel_id})" if channel is None else channel.mention
            
            server_type = server_data.get("type", "java").upper()
            rcon_status = "Включён" if server_data.get("rcon", {}).get("enabled", False) else "Выключен"
            status_display = "IP" if server_data.get("display_in_status", "players") == "ip" else "Игроки"
            
            embed.add_field(
                name=f"{server_type} Сервер: {server_data['address']}",
                value=(
                    f"Канал: {channel_name}\n"
                    f"Статус: {server_data.get('last_status', 'неизвестно')}\n"
                    f"Отображение игроков: {'Да' if server_data['players'] else 'Нет'}\n"
                    f"RCON: {rcon_status}\n"
                    f"В статусе бота: {'Да' if server_data.get('show_in_status', False) else 'Нет'}\n"
                    f"Отображать в статусе: {status_display}"
                ),
                inline=False
            )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="action", description="Управление сервером")
    async def server_action(self, interaction: discord.Interaction):
        if not any(role.id in allowed_role_ids for role in interaction.user.roles):
            embed = discord.Embed(
                title="Ошибка",
                description="У вас недостаточно прав для выполнения этой команды.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        if not self.server_info:
            embed = discord.Embed(
                title="Ошибка",
                description="Нет отслеживаемых серверов.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        view = discord.ui.View()
        view.add_item(ServerSelectDropdown(self, self.server_info))
        await interaction.response.send_message(
            "Выберите сервер для управления:",
            view=view,
            ephemeral=True
        )

    async def update_server_embed(self, channel):
        if channel.id not in self.server_info:
            return

        server_data = self.server_info[channel.id]
        address = server_data["address"]
        server_type = server_data.get("type", "java")
        player_list = server_data["players"]
        last_status = server_data["last_status"]

        status = await self.get_server_status(server_type, address)

        if status["online"]:
            players_online = status["players"]
            players_max = status["max_players"]
            players = status["player_list"]
            version = status["version"]
            latency = int(status["latency"])

            embed = discord.Embed(
                title=f"Сервер {address} онлайн",
                description=f"**Версия:** {version}\n**Игроков:** {players_online}/{players_max}\n**Пинг:** {latency}мс",
                color=discord.Color.green()
            )
            
            if player_list and players:
                embed.add_field(
                    name="Игроки онлайн:",
                    value="\n".join(players) if players else "Информация недоступна",
                    inline=False
                )

            if server_data.get("rename_channel", True):
                try:
                    await channel.edit(name=f"mc-{address.replace(':', '-')}-online")
                except:
                    pass

            server_data["last_status"] = "online"
        else:
            embed = discord.Embed(
                title=f"Сервер {address} оффлайн",
                description="Сервер не отвечает или недоступен.",
                color=discord.Color.red()
            )
            
            if server_data.get("rename_channel", True):
                try:
                    await channel.edit(name=f"mc-{address.replace(':', '-')}-offline")
                except:
                    pass

            server_data["last_status"] = "offline"

        try:
            if server_data["message"] is None:
                message = await channel.send(embed=embed)
                server_data["message"] = message.id
                self.save_data()
            else:
                try:
                    message = await channel.fetch_message(server_data["message"])
                    await message.edit(embed=embed)
                except discord.NotFound:
                    message = await channel.send(embed=embed)
                    server_data["message"] = message.id
                    self.save_data()
                except discord.Forbidden:
                    pass
        except Exception as e:
            print(f"Ошибка обновления embed: {e}")

    @tasks.loop(minutes=1)
    async def update_embed(self):
        channels_to_remove = []
        
        for channel_id in list(self.server_info.keys()):
            channel = self.bot.get_channel(channel_id)
            if channel is None:
                channels_to_remove.append(channel_id)
                continue
            
            server_data = self.server_info[channel_id]
            if server_data["message"] is not None:
                try:
                    await channel.fetch_message(server_data["message"])
                except discord.NotFound:
                    channels_to_remove.append(channel_id)
                    continue
                except discord.Forbidden:
                    pass
            
            await self.update_server_embed(channel)
        
        for channel_id in channels_to_remove:
            del self.server_info[channel_id]
        
        if channels_to_remove:
            self.save_data()

    @tasks.loop(minutes=2)
    async def update_status(self):
        servers_in_status = [
            server for server in self.server_info.values() 
            if server.get("show_in_status", False)
        ]
        
        if not servers_in_status:
            await self.bot.change_presence(activity=None)
            return

        status_messages = []
        for server in servers_in_status:
            address = server["address"]
            if ":" in address:
                host, port = address.split(":")
                if port in ("25565", "19132"):
                    address = host

            if server.get("display_in_status", "players") == "players" and server["last_status"] == "online":
                status = await self.get_server_status(server.get("type", "java"), server["address"])
                if status["online"]:
                    status_messages.append(f"{address}: {status['players']}👥")
                else:
                    status_messages.append(f"{address}: оффлайн")
            else:
                status_messages.append(address)

        activity = discord.Activity(
            name=" | ".join(status_messages),
            type=discord.ActivityType.watching
        )
        await self.bot.change_presence(activity=activity)

    @update_embed.before_loop
    async def before_update_embed(self):
        await self.bot.wait_until_ready()

    @update_status.before_loop
    async def before_update_status(self):
        await self.bot.wait_until_ready()

class ServerSelectDropdown(discord.ui.Select):
    def __init__(self, cog, server_info):
        self.cog = cog
        options = []
        for channel_id, server_data in server_info.items():
            server_type = server_data.get("type", "java").upper()
            options.append(
                discord.SelectOption(
                    label=f"{server_type} - {server_data['address']}",
                    value=str(channel_id),
                    description=f"Канал ID: {channel_id}"
                )
            )
        
        super().__init__(
            placeholder="Выберите сервер...",
            min_values=1,
            max_values=1,
            options=options
        )
    
    async def callback(self, interaction: discord.Interaction):
        channel_id = int(self.values[0])
        server_data = self.cog.server_info[channel_id]
        
        modal = ServerSettingsModal(self.cog, server_data, channel_id)
        await interaction.response.send_modal(modal)

class ServerSettingsModal(discord.ui.Modal):
    def __init__(self, cog, server_data, channel_id):
        super().__init__(title="Настройки сервера")
        self.cog = cog
        self.server_data = server_data
        self.channel_id = channel_id
        
        self.add_item(discord.ui.TextInput(
            label="Адрес сервера (host:port)",
            default=server_data["address"],
            required=True
        ))
        
        self.add_item(discord.ui.TextInput(
            label="Тип сервера (java/bedrock)",
            default=server_data.get("type", "java"),
            required=True
        ))
        
        self.add_item(discord.ui.TextInput(
            label="Порт RCON (оставьте пустым для отключения)",
            default=str(server_data.get("rcon", {}).get("port", "")),
            required=False
        ))
        
        self.add_item(discord.ui.TextInput(
            label="Пароль RCON",
            default=server_data.get("rcon", {}).get("password", ""),
            required=False,
            style=discord.TextStyle.short
        ))
        
        self.add_item(discord.ui.TextInput(
            label="ID канала для логов RCON",
            default=str(server_data.get("rcon", {}).get("log_channel", "")),
            required=False
        ))

    async def on_submit(self, interaction: discord.Interaction):
        self.server_data["address"] = self.children[0].value
        self.server_data["type"] = self.children[1].value.lower()
        
        rcon_port = self.children[2].value.strip()
        rcon_password = self.children[3].value.strip()
        rcon_log_channel = self.children[4].value.strip()
        
        if rcon_port and rcon_password:
            self.server_data["rcon"] = {
                "enabled": True,
                "port": int(rcon_port),
                "password": rcon_password
            }
            if rcon_log_channel:
                self.server_data["rcon"]["log_channel"] = int(rcon_log_channel)
        else:
            self.server_data["rcon"] = {"enabled": False}
        
        self.cog.server_info[self.channel_id] = self.server_data
        self.cog.save_data()
        
        embed = discord.Embed(
            title="Настройки обновлены",
            description="Настройки сервера успешно сохранены.",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        
        channel = interaction.guild.get_channel(self.channel_id)
        if channel:
            await self.cog.update_server_embed(channel)

class ServerSettingsView(discord.ui.View):
    def __init__(self, cog, server_data, channel_id):
        super().__init__()
        self.cog = cog
        self.server_data = server_data
        self.channel_id = channel_id
        
        self.add_item(discord.ui.Button(
            label="Игроки/IP в статусе",
            style=discord.ButtonStyle.primary,
            custom_id="status_display"
        ))
        self.add_item(discord.ui.Button(
            label="Показывать в статусе бота",
            style=discord.ButtonStyle.secondary,
            custom_id="show_in_status"
        ))
        self.add_item(discord.ui.Button(
            label="Переименовывать канал",
            style=discord.ButtonStyle.secondary,
            custom_id="rename_channel"
        ))
        self.add_item(discord.ui.Button(
            label="Удалить сервер",
            style=discord.ButtonStyle.danger,
            custom_id="delete_server"
        ))

    async def interaction_check(self, interaction: discord.Interaction):
        if not any(role.id in allowed_role_ids for role in interaction.user.roles):
            await interaction.response.send_message(
                "У вас недостаточно прав для этого действия.",
                ephemeral=True
            )
            return False
        return True

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True
        try:
            await self.message.edit(view=self)
        except:
            pass

async def setup(bot):
    await bot.add_cog(Minecraft(bot))

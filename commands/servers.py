import discord
import os


async def list_servers(interaction: discord.Interaction):
    guild_info = [(guild.name, str(guild.id))
                  for guild in interaction.client.guilds]
    guild_list = "\n".join([f"{name} (ID: {id})" for name, id in guild_info])

    # Specify the file path within the "Documents" directory
    file_path = os.path.join(os.path.expanduser(
        "~"), "Documents", "server_list.txt")

    try:
        with open(file_path, "w", encoding="utf-8") as file:
            file.write(guild_list)
        await interaction.response.send_message(f"Server list saved to `{file_path}`.")
    except Exception as e:
        await interaction.response.send_message(f"Error saving server list: {e}")


def setup(client):
    client.tree.command(
        name="list_servers", description="List all servers the bot is in")(list_servers)

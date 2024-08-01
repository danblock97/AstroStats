import discord
from discord.ext import commands

# Function to read the content of the .txt file
def read_update_file(filepath: str) -> str:
    try:
        with open(filepath, 'r') as file:
            content = file.read().strip()
            if not content:
                return "The update file is empty."
            return content
    except Exception as e:
        return f"Error reading file: {e}"

# Command to show the latest update
async def show_update(ctx: commands.Context):
    print(f"Show update command called from server ID: {ctx.guild.id}")
    filepath = 'updates.txt'  # Path to the .txt file
    update_content = read_update_file(filepath)
    await ctx.send(update_content)

def setup(client):
    client.add_command(commands.Command(show_update, name="show_update"))

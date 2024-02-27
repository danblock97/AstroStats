import discord


async def kick_server(interaction: discord.Interaction, guild_id: str):
    try:
        guild = interaction.client.get_guild(int(guild_id))
        if guild:
            await guild.leave()
            await interaction.response.send_message(f"Successfully kicked the bot from the server with ID: {guild_id}")
        else:
            await interaction.response.send_message(f"Error: Server with ID {guild_id} not found.")
    except Exception as e:
        await interaction.response.send_message(f"Error kicking the bot from the server: {e}")


def setup(client):
    client.tree.command(
        name="kick_server", description="Kick the bot from a specific server"
    )(kick_server)

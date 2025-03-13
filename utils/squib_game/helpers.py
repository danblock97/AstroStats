import discord

async def get_guild_avatar_url(guild: discord.Guild, user_id: int) -> str:
    try:
        member = await guild.fetch_member(user_id)
        if member and member.guild_avatar:
            return member.guild_avatar.url
        elif member:
            return member.display_avatar.url
        else:
            return None
    except Exception:
        return None

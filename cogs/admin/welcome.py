import io
import logging
import base64
import aiohttp
from PIL import Image
import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional, Literal, List

from services.premium import get_user_entitlements
from services.database.welcome import get_welcome_settings, update_welcome_settings
from ui.embeds import get_premium_promotion_view

logger = logging.getLogger(__name__)


def has_required_tier(required_tiers: List[str]):
    """Check if user has required premium tier."""
    async def predicate(interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        ent = get_user_entitlements(user_id)
        user_tier = ent.get("tier", "free")
        
        if user_tier in required_tiers:
            return True
        
        # Send error message with premium promotion
        embed = discord.Embed(
            title="🔒 Premium Feature Required",
            description=f"This feature requires **{' or '.join(required_tiers).title()}** tier or higher.",
            color=discord.Color.gold()
        )
        embed.add_field(
            name="Your Current Tier", 
            value=user_tier.title(), 
            inline=False
        )
        
        view = get_premium_promotion_view() if user_tier == "free" else None
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        return False
    
    return app_commands.check(predicate)


def has_manage_guild_permission():
    """Check if user has manage guild permission."""
    async def predicate(interaction: discord.Interaction):
        if not interaction.user.guild_permissions.manage_guild:
            embed = discord.Embed(
                title="❌ Missing Permissions",
                description="You need the **Manage Server** permission to use this command.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return False
        return True
    
    return app_commands.check(predicate)


async def compress_image(image_data: bytes, max_size_mb: int = 8, preserve_gif: bool = False) -> Optional[bytes]:
    """Compress image to fit within Discord's size limit."""
    try:
        # Check if it's a GIF and preserve_gif is True
        if preserve_gif:
            # For GIFs, just check size and return as-is if small enough
            size_mb = len(image_data) / (1024 * 1024)
            if size_mb <= max_size_mb:
                return image_data
            else:
                # GIF is too large, we'll still try to compress it
                pass
        
        # Open the image
        image = Image.open(io.BytesIO(image_data))
        
        # Handle GIF specifically
        if image.format == 'GIF' and preserve_gif:
            # Try to optimize GIF without losing animation
            output = io.BytesIO()
            image.save(output, format="GIF", optimize=True, save_all=True)
            size_mb = len(output.getvalue()) / (1024 * 1024)
            if size_mb <= max_size_mb:
                return output.getvalue()
        
        # Convert to RGB if needed (for WEBP compatibility)
        if image.mode in ("RGBA", "P"):
            image = image.convert("RGB")
        
        # Start with high quality
        quality = 95
        
        while quality > 10:
            output = io.BytesIO()
            image.save(output, format="WEBP", quality=quality, optimize=True)
            size_mb = len(output.getvalue()) / (1024 * 1024)
            
            if size_mb <= max_size_mb:
                return output.getvalue()
            
            quality -= 10
        
        # If still too large, resize the image
        if quality <= 10:
            width, height = image.size
            # Reduce dimensions by 20% each iteration
            while True:
                width = int(width * 0.8)
                height = int(height * 0.8)
                
                resized_image = image.resize((width, height), Image.Resampling.LANCZOS)
                output = io.BytesIO()
                resized_image.save(output, format="WEBP", quality=85, optimize=True)
                size_mb = len(output.getvalue()) / (1024 * 1024)
                
                if size_mb <= max_size_mb or width < 100 or height < 100:
                    return output.getvalue() if size_mb <= max_size_mb else None
        
        return None
    except Exception as e:
        logger.error(f"Error compressing image: {e}")
        return None


class WelcomeCog(commands.GroupCog, group_name="welcome"):
    """Welcome system for new members."""

    def __init__(self, bot: commands.Bot):
        super().__init__()
        self.bot = bot

    @app_commands.command(name="toggle", description="Enable or disable welcome messages for new members")
    @has_manage_guild_permission()
    async def toggle_welcome(
        self, 
        interaction: discord.Interaction, 
        enabled: Literal["true", "false"]
    ):
        """Toggle welcome messages on or off."""
        guild_id = str(interaction.guild.id)
        is_enabled = enabled == "true"
        
        # Update the database
        success = update_welcome_settings(guild_id, enabled=is_enabled)
        
        if not success:
            embed = discord.Embed(
                title="❌ Error",
                description="Failed to update welcome settings. Please try again.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        status = "enabled" if is_enabled else "disabled"
        embed = discord.Embed(
            title="✅ Welcome Settings Updated",
            description=f"Welcome messages have been **{status}** for this server.",
            color=discord.Color.green()
        )
        
        if is_enabled:
            system_channel = interaction.guild.system_channel
            channel_mention = system_channel.mention if system_channel else "the system messages channel"
            embed.add_field(
                name="📍 Where messages will be sent",
                value=f"New members will be welcomed in {channel_mention}.",
                inline=False
            )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="set-message", description="Set a custom welcome message (Premium feature)")
    @has_manage_guild_permission()
    @has_required_tier(["supporter", "sponsor", "vip"])
    async def set_message(self, interaction: discord.Interaction, message: str):
        """Set a custom welcome message."""
        if len(message) > 1000:
            embed = discord.Embed(
                title="❌ Message Too Long",
                description="Welcome messages must be 1000 characters or less.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        guild_id = str(interaction.guild.id)
        success = update_welcome_settings(guild_id, custom_message=message)
        
        if not success:
            embed = discord.Embed(
                title="❌ Error",
                description="Failed to update welcome message. Please try again.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        embed = discord.Embed(
            title="✅ Custom Welcome Message Set",
            description="Your custom welcome message has been saved!",
            color=discord.Color.green()
        )
        
        # Show a preview of the message with placeholders replaced
        preview_message = message.replace("{user}", interaction.user.mention).replace("{username}", interaction.user.display_name).replace("{server}", interaction.guild.name)
        
        # Replace channel mentions in preview too
        import re
        def replace_channel_mention_preview(match):
            channel_name = match.group(1)
            # Find channel by name (case insensitive)
            for channel in interaction.guild.text_channels:
                if channel.name.lower() == channel_name.lower():
                    return channel.mention
            # If channel not found, return original text
            return f"#{channel_name}"
        
        preview_message = re.sub(r'\{#([^}]+)\}', replace_channel_mention_preview, preview_message)
        
        embed.add_field(
            name="📝 Preview",
            value=preview_message[:500] + ("..." if len(preview_message) > 500 else ""),
            inline=False
        )
        
        embed.add_field(
            name="💡 Available Placeholders",
            value=(
                "`{user}` - Mentions the new member\n"
                "`{username}` - New member's display name\n"
                "`{server}` - Server name\n"
                "`{#channel-name}` - Links to a channel"
            ),
            inline=False
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="remove-message", description="Remove the custom welcome message")
    @has_manage_guild_permission()
    async def remove_message(self, interaction: discord.Interaction):
        """Remove the custom welcome message."""
        guild_id = str(interaction.guild.id)
        success = update_welcome_settings(guild_id, custom_message=None)
        
        if not success:
            embed = discord.Embed(
                title="❌ Error",
                description="Failed to remove welcome message. Please try again.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        embed = discord.Embed(
            title="✅ Custom Message Removed",
            description="The custom welcome message has been removed. New members will receive the default welcome message.",
            color=discord.Color.green()
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="set-image", description="Set a custom welcome image (Sponsor/VIP feature)")
    @has_manage_guild_permission() 
    @has_required_tier(["sponsor", "vip"])
    async def set_image(self, interaction: discord.Interaction, image: discord.Attachment):
        """Set a custom welcome image."""
        # Validate file type
        allowed_formats = ['png', 'jpg', 'jpeg', 'webp', 'gif', 'bmp']
        file_extension = image.filename.split('.')[-1].lower()
        
        if file_extension not in allowed_formats:
            embed = discord.Embed(
                title="❌ Invalid File Format",
                description=f"Please upload an image with one of these formats: {', '.join(allowed_formats).upper()}",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Defer response as image processing might take time (especially on mobile)
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Download the image
            image_data = await image.read()
            
            # Check if it's a GIF to preserve animation
            is_gif = file_extension == 'gif'
            
            # Compress the image (preserve GIF animation if applicable)
            compressed_data = await compress_image(image_data, preserve_gif=is_gif)
            
            if compressed_data is None:
                embed = discord.Embed(
                    title="❌ Image Too Large",
                    description="The image is too large even after compression. Please choose a smaller image or compress it yourself.",
                    color=discord.Color.red()
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            # Convert compressed image to base64 for MongoDB storage
            image_base64 = base64.b64encode(compressed_data).decode('utf-8')
            
            # Save the image data to database
            guild_id = str(interaction.guild.id)
            success = update_welcome_settings(
                guild_id, 
                custom_image_data=image_base64,
                custom_image_filename=image.filename
            )
            
            if not success:
                embed = discord.Embed(
                    title="❌ Database Error",
                    description="Failed to save the welcome image. Please try again.",
                    color=discord.Color.red()
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            embed = discord.Embed(
                title="✅ Custom Welcome Image Set",
                description="Your custom welcome image has been saved to the database!",
                color=discord.Color.green()
            )
            
            compressed_size_mb = len(compressed_data) / (1024 * 1024)
            original_size_mb = len(image_data) / (1024 * 1024)
            format_info = "GIF (animated)" if is_gif else "WEBP"
            embed.add_field(
                name="📊 Image Info",
                value=f"Original: {original_size_mb:.1f}MB → Compressed: {compressed_size_mb:.1f}MB ({format_info})",
                inline=False
            )
            embed.add_field(
                name="💾 Storage",
                value="Image stored securely in database",
                inline=False
            )
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error setting welcome image for guild {interaction.guild.id}: {e}")
            embed = discord.Embed(
                title="❌ Upload Failed",
                description="An error occurred while processing your image. Please try again.",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="remove-image", description="Remove the custom welcome image (Sponsor/VIP feature)")
    @has_manage_guild_permission()
    @has_required_tier(["sponsor", "vip"])
    async def remove_image(self, interaction: discord.Interaction):
        """Remove the custom welcome image."""
        guild_id = str(interaction.guild.id)
        success = update_welcome_settings(guild_id, custom_image_data=None, custom_image_filename=None)
        
        if not success:
            embed = discord.Embed(
                title="❌ Error",
                description="Failed to remove welcome image. Please try again.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        embed = discord.Embed(
            title="✅ Custom Image Removed",
            description="The custom welcome image has been removed.",
            color=discord.Color.green()
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="test", description="Test the welcome message by sending a preview")
    @has_manage_guild_permission()
    async def test_welcome(self, interaction: discord.Interaction):
        """Test/preview the welcome message."""
        guild_id = str(interaction.guild.id)
        welcome_settings = get_welcome_settings(guild_id)
        
        # Check if welcome is enabled
        if not welcome_settings or not welcome_settings.enabled:
            embed = discord.Embed(
                title="⚠️ Welcome Messages Disabled",
                description="Welcome messages are currently disabled. Use `/welcome toggle true` to enable them first.",
                color=discord.Color.orange()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Find the target channel (same logic as actual welcome)
        target_channel = interaction.guild.system_channel
        if target_channel is None or not target_channel.permissions_for(interaction.guild.me).send_messages:
            for channel in interaction.guild.text_channels:
                if channel.permissions_for(interaction.guild.me).send_messages:
                    target_channel = channel
                    break
        
        if target_channel is None:
            embed = discord.Embed(
                title="❌ No Available Channel",
                description="I couldn't find a channel to send welcome messages to. Please ensure I have permission to send messages in at least one channel.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Create the test welcome message (using the command user as example)
        if welcome_settings.custom_message:
            # Use custom message with placeholder replacement
            message_content = welcome_settings.custom_message.replace(
                "{user}", interaction.user.mention
            ).replace(
                "{username}", interaction.user.display_name
            ).replace(
                "{server}", interaction.guild.name
            )
            
            # Replace channel mentions like {#channel-name} with actual channel mentions
            import re
            def replace_channel_mention(match):
                channel_name = match.group(1)
                # Find channel by name (case insensitive)
                for channel in interaction.guild.text_channels:
                    if channel.name.lower() == channel_name.lower():
                        return channel.mention
                # If channel not found, return original text
                return f"#{channel_name}"
            
            message_content = re.sub(r'\{#([^}]+)\}', replace_channel_mention, message_content)
        else:
            # Use default welcome message
            message_content = f"Welcome {interaction.user.mention} to **{interaction.guild.name}**! Please verify yourself and get to know everyone!"
        
        # Add test indicator to the message
        test_message = f"{message_content}\n\n*🧪 This is a test welcome message*"
        
        try:
            # Send message with optional image attachment in single message
            if welcome_settings.custom_image_data:
                try:
                    # Decode base64 image data and send with text
                    image_bytes = base64.b64decode(welcome_settings.custom_image_data)
                    filename = welcome_settings.custom_image_filename or "welcome_image.webp"
                    file = discord.File(io.BytesIO(image_bytes), filename=filename)
                    await target_channel.send(content=test_message, file=file)
                except Exception as e:
                    logger.error(f"Error sending test welcome image: {e}")
                    # Fallback to text only if image fails
                    await target_channel.send(content=test_message)
            else:
                # Send just the text message
                await target_channel.send(content=test_message)
            
            # Confirm to the user
            confirm_embed = discord.Embed(
                title="✅ Test Message Sent",
                description=f"Preview welcome message sent to {target_channel.mention}",
                color=discord.Color.green()
            )
            await interaction.response.send_message(embed=confirm_embed, ephemeral=True)
            
        except discord.Forbidden:
            embed = discord.Embed(
                title="❌ Permission Error",
                description=f"I don't have permission to send messages in {target_channel.mention}",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            logger.error(f"Error sending test welcome message: {e}")
            embed = discord.Embed(
                title="❌ Error",
                description="Failed to send test welcome message. Please try again.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(WelcomeCog(bot))
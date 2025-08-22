import discord
from discord.ext import commands
from discord import app_commands

from services.premium import get_user_entitlements


PRICING = {
    "free": {
        "price": "£0",
        "benefits": [
            "3 daily quests",
            "1 pet capacity",
            "Standard SquibGames cap",
            "Basic welcome messages",
            "Welcome toggle on/off",
        ],
    },
    "supporter": {
        "price": "£3/mo",
        "benefits": [
            "+2 daily quests (total 5)",
            "+0 extra pets (1 total)",
            "SquibGames cap 20",
            "Premium badge",
            "Premium-only commands",
            "1.2x XP & cash",
            "Custom welcome messages",
        ],
    },
    "sponsor": {
        "price": "£5/mo",
        "benefits": [
            "+5 daily quests (total 8)",
            "+1 extra pets (2 total)",
            "SquibGames cap 50",
            "Premium badge",
            "Premium-only commands",
            "1.5x XP & cash",
            "Custom welcome messages",
            "Custom welcome images",
        ],
    },
    "vip": {
        "price": "£10/mo",
        "benefits": [
            "+8 daily quests (total 11)",
            "+3 extra pets (4 total)",
            "SquibGames cap 75",
            "Premium badge",
            "Premium-only commands",
            "1.75x XP & cash",
            "Custom welcome messages",
            "Custom welcome images",
        ],
    },
}


class PremiumCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="premium", description="View AstroStats Premium tiers, pricing, and benefits")
    async def premium(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        ent = get_user_entitlements(user_id)
        current_tier = ent.get("tier", "free").title()
        site_url = "https://astrostats.info"

        embed = discord.Embed(
            title="🌟 AstroStats Premium",
            description=(
                "Level up your experience with more quests, pets, and bigger games. "
                f"Manage or upgrade at {site_url}"
            ),
            color=discord.Color.gold()
        )
        embed.set_footer(text="Built By Goldiez ❤️ Support: astrostats.info")

        embed.add_field(name="Your Tier", value=f"{current_tier}", inline=False)

        for tier_key in ["free", "supporter", "sponsor", "vip"]:
            tier = PRICING[tier_key]
            name = tier_key.title()
            price = tier["price"]
            benefits = "\n".join([f"• {b}" for b in tier["benefits"]])
            embed.add_field(
                name=f"{name} — {price}",
                value=benefits,
                inline=False
            )

        embed.add_field(
            name="Get Premium",
            value=f"Visit {site_url} to subscribe, manage, or learn more.",
            inline=False
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(PremiumCog(bot))



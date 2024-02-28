import discord
from discord.ext import commands
import datetime
import requests
import os

async def fortnite(interaction: discord.Interaction, *, name: str):
    try:
        response = requests.get(
            f"https://fortnite-api.com/v2/stats/br/v2?timeWindow=season&name={name}",
            headers={"Authorization": os.getenv('FORTNITE_API_KEY')}
        )

        response.raise_for_status()
        data = response.json()

        if 'data' not in data:
            raise ValueError("Invalid data structure in API response.")

        stats = data['data']
        account = stats['account']
        battlePass = stats['battlePass']

        embed = discord.Embed(title=f"Fortnite - Player Stats", color=0xdd4f7a)

        embed.add_field(name="Account", value=f"Name: {account['name']}\nLevel: {battlePass['level']}")
        embed.add_field(name="Season Stats",
                        value=f"Matches: {stats['stats']['all']['overall']['matches']}\nKills: {stats['stats']['all']['overall']['kills']}\nWins: {stats['stats']['all']['overall']['wins']}")
        embed.add_field(name="Match Placements",
                        value=f"Top 5: {stats['stats']['all']['overall']['top5']}\nTop 12: {stats['stats']['all']['overall']['top12']}")
        embed.timestamp = datetime.datetime.utcnow()
        embed.set_footer(text="Need Support? | Visit astrostats.vercel.app | Built By Goldiez ❤️")
        await interaction.response.send_message(embed=embed)

    except requests.exceptions.RequestException as e:
        print(f"Error: {e}")
        await interaction.response.send_message("Sorry, I couldn't retrieve Fortnite stats at the moment. Please try again later.")

    except (KeyError, ValueError) as e:
        print(f"Error: {e}")
        await interaction.response.send_message("Failed to retrieve Fortnite stats. The Fortnite API is Currently Unavailable")

    except Exception as e:
        print(f"Error: {e}")
        await interaction.response.send_message("Oops! An unexpected error occurred while processing your request. Please try again later.")

def setup(client):
    client.tree.command(
        name="fortnite", description="Check your Fortnite Player Stats"
    )(fortnite)

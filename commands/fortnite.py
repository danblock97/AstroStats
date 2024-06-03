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
        battle_pass = stats['battlePass']

        embed = discord.Embed(title=f"Fortnite - {name}", color=0xdd4f7a,
                              url=f"https://fortnitetracker.com/profile/all/{name}")
        embed.set_thumbnail(url="https://seeklogo.com/images/F/fortnite-logo-1F7897BD1E-seeklogo.com.png")
        embed.add_field(name="Account", value=f"Name: {account['name']}\nLevel: {battle_pass['level']}")
        embed.add_field(name="Match Placements",
                        value=f"Top 5: {stats['stats']['all']['overall']['top5']}\nTop 12: {stats['stats']['all']['overall']['top12']}")

        # Additional Stats
        embed.add_field(name="Season Stats",
                        value=f"Total Score: {stats['stats']['all']['overall']['score']:,}\n"
                              f"Score Per Minute: {stats['stats']['all']['overall']['scorePerMin']:.0f}\n"
                              f"Score Per Match: {stats['stats']['all']['overall']['scorePerMatch']:.0f}\n"
                              f"Total Kills: {stats['stats']['all']['overall']['kills']:,}\n"
                              f"Kills Per Minute: {stats['stats']['all']['overall']['killsPerMin']:.2f}\n"
                              f"Kills Per Match: {stats['stats']['all']['overall']['killsPerMatch']:.2f}\n"
                              f"Total Deaths: {stats['stats']['all']['overall']['deaths']:,}\n"
                              f"KD Ratio: {stats['stats']['all']['overall']['kd']:.2f}\n"
                              f"Total Matches Played: {stats['stats']['all']['overall']['matches']:,}\n"
                              f"Win Rate: {stats['stats']['all']['overall']['winRate']:.2%}\n"
                              f"Total Minutes Played: {stats['stats']['all']['overall']['minutesPlayed']:,}\n"
                              f"Players Outlived: {stats['stats']['all']['overall']['playersOutlived']:,}",
                        inline=False)

        # Similar fields can be added for Solo, Duo, Trio, Squad, LTMs, Input Methods, etc.

        embed.timestamp = datetime.datetime.now(datetime.UTC)
        embed.set_footer(text="Built By Goldiez ❤️")
        await interaction.response.send_message(embed=embed)

    except requests.exceptions.RequestException as e:
        print(f"Error: {e}")
        await interaction.response.send_message(
            "Sorry, I couldn't retrieve Fortnite stats at the moment. Please try again later.")

    except (KeyError, ValueError) as e:
        print(f"Error: {e}")
        await interaction.response.send_message(
            "Failed to retrieve Fortnite stats. The Fortnite API is Currently Unavailable")

    except Exception as e:
        print(f"Error: {e}")
        await interaction.response.send_message(
            "Oops! An unexpected error occurred while processing your request. Please try again later.")


def setup(client):
    client.tree.command(
        name="fortnite", description="Check your Fortnite Player Stats"
    )(fortnite)

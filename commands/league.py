import discord
import datetime
import requests
from riotwatcher import LolWatcher
from typing import Literal
import os

Region = Literal['Brazil', 'Europe Nordic & East', 'Europe', 'Japan', 'Korea', 'Latin America North',
                 'Latin America South', 'North America', 'Oceania', 'Turkey', 'Russia', 'Philippines', 'Singapore']


async def league(interaction: discord.Interaction, region: Region, *, summoner: str):
    # Define a dictionary to map display names to Riot API region codes
    region_mapping = {
        "Brazil": "br1",
        "Europe Nordic & East": "eun1",
        "Europe": "euw1",
        "Japan": "jp1",
        "Korea": "kr",
        "Latin America North": "la1",
        "Latin America South": "la2",
        "North America": "na1",
        "Oceania": "oc1",
        "Turkey": "tr1",
        "Russia": "ru",
        "Philippines": "ph2",
        "Singapore": "sg2",
    }

    # Check if the provided region is valid
    if region not in region_mapping:
        await interaction.response.send_message("Invalid region. Please use a valid region name.")
        return

    try:
        # Get the Riot API region code from the dictionary
        riot_region = region_mapping[region]

        lolWatcher = LolWatcher(os.getenv('RIOT_API'))
        summoner = lolWatcher.summoner.by_name(riot_region, summoner)
        stats = lolWatcher.league.by_summoner(riot_region, summoner['id'])

        num = 0 if stats and stats[0]['queueType'] == 'RANKED_SOLO_5x5' else 1

        if not stats or not stats[num]:
            raise ValueError("Invalid data structure in API response.")

        tier = stats[num]['tier']
        rank = stats[num]['rank']
        lp = stats[num]['leaguePoints']
        wins = int(stats[num]['wins'])
        losses = int(stats[num]['losses'])
        wr = int((wins / (wins + losses)) * 100)
        hotStreak = int(stats[num]['hotStreak'])
        level = int(summoner['summonerLevel'])
        icon = int(summoner['profileIconId'])

        embed = discord.Embed(
            title=f"League of Legends - Player Stats", color=0xdd4f7a)
        embed.set_thumbnail(
            url=f"https://raw.communitydragon.org/latest/plugins/rcp-be-lol-game-data/global/default/v1/profile-icons/{icon}.jpg")
        embed.add_field(name="Ranked Solo/Duo",
                        value=f'{str(tier)} {str(rank)} {str(lp)} LP \n Winrate: {str(wr)}% \n Winstreak: {str(hotStreak)}')
        embed.add_field(name="Level", value=f'{str(level)}')
        embed.timestamp = datetime.datetime.utcnow()
        embed.set_footer(text="Need Support? | Visit astrostats.vercel.app | Built By Goldiez ❤️")

        await interaction.response.send_message(embed=embed)

    except requests.exceptions.RequestException as e:
        print(f"Error: {e}")
        await interaction.response.send_message("Sorry, I couldn't retrieve League of Legends stats at the moment. Please try again later.")

    except (KeyError, ValueError) as e:
        print(f"Error: {e}")
        await interaction.response.send_message("Failed to retrieve League of Legends stats. The service may be currently unavailable.")

    except Exception as e:
        print(f"Error: {e}")
        await interaction.response.send_message("Oops! An unexpected error occurred while processing your request. Please try again later.")


def setup(client):
    client.tree.command(
        name="league", description="Check your LoL Player Stats"
    )(league)

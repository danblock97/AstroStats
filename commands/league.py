import discord
import datetime
from riotwatcher import LolWatcher
import os

async def league(interaction: discord.Interaction, region: str, *, summoner: str):
    print(f"League command called with region: {region} and summoner: {summoner}")
    # Define a dictionary to map region names to Riot API region codes
    region_mapping = {
        "b1": "br1",
        "eun": "eun1",
        "euw": "euw1",
        "jp": "jp1",
        "kr": "kr",
        "lan": "la1",
        "las": "la2",
        "na": "na1",
        "oc": "oc1",
        "tr": "tr1",
        "ru": "ru",
        "ph": "ph2",
        "sg": "sg2",
        "th": "th2",
        "tw": "tw2",
        "vn": "vn2",
    }

    # Check if the provided region is valid
    if region.lower() not in region_mapping:
        await interaction.response.send_message("Invalid region. Please use a valid region code (e.g., 'na', 'euw').")
        return

    try:
        # Get the Riot API region code from the dictionary
        riot_region = region_mapping[region.lower()]

        lolWatcher = LolWatcher(os.getenv('RIOT_API'))
        summoner = lolWatcher.summoner.by_name(riot_region, summoner)
        stats = lolWatcher.league.by_summoner(riot_region, summoner['id'])

        num = 0 if stats[0]['queueType'] == 'RANKED_SOLO_5x5' else 1
        tier = stats[num]['tier']
        rank = stats[num]['rank']
        lp = stats[num]['leaguePoints']
        wins = int(stats[num]['wins'])
        losses = int(stats[num]['losses'])
        wr = int((wins / (wins + losses)) * 100)
        hotStreak = int(stats[num]['hotStreak'])
        level = int(summoner['summonerLevel'])
        icon = int(summoner['profileIconId'])

        embed = discord.Embed(title=f"League of Legends - Player Stats", color=0xdd4f7a)
        embed.set_thumbnail(
            url=f"https://raw.communitydragon.org/latest/plugins/rcp-be-lol-game-data/global/default/v1/profile-icons/{icon}.jpg")
        embed.add_field(name="Ranked Solo/Duo",
                        value=f'{str(tier)} {str(rank)} {str(lp)} LP \n Winrate: {str(wr)}% \n Winstreak: {str(hotStreak)}')
        embed.add_field(name="Level", value=f'{str(level)}')
        embed.timestamp = datetime.datetime.utcnow()
        embed.set_footer(text="Built By Goldiez" "\u2764\uFE0F")
        await interaction.response.send_message(embed=embed)
    except Exception as e:
        error_message = "Please use your old Summoner Name for now.. Riot Names are not implemented yet."
        await interaction.response.send_message(error_message)



def setup(client):
    client.tree.command(name="league", description="Check your LoL Player Stats")(league)

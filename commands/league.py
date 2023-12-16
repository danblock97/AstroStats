import discord
import datetime
from riotwatcher import LolWatcher
import os

async def league(interaction: discord.Interaction, *, summoner: str):
    try:
        lolWatcher = LolWatcher(os.getenv('RIOT_API'))
        summoner = lolWatcher.summoner.by_name('euw1', summoner)
        stats = lolWatcher.league.by_summoner('euw1', summoner['id'])

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

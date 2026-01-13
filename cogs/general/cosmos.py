import discord
from discord.ext import commands
from discord import app_commands
import aiohttp
import os
import datetime
import time

class Cosmos(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.launch_cache = None
        self.launch_cache_time = 0
        self.LAUNCH_CACHE_DURATION = 900  # 15 minutes in seconds

    @app_commands.command(name="apod", description="Get NASA's Astronomy Picture of the Day")
    async def apod(self, interaction: discord.Interaction):
        """Fetches and displays NASA's Astronomy Picture of the Day."""
        await interaction.response.defer()
        
        api_key = os.getenv("NASA_API_KEY", "DEMO_KEY")
        url = f"https://api.nasa.gov/planetary/apod?api_key={api_key}"

        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        title = data.get("title", "Astronomy Picture of the Day")
                        date = data.get("date", "Unknown Date")
                        explanation = data.get("explanation", "No explanation available.")
                        media_url = data.get("url")
                        hd_url = data.get("hdurl")
                        copyright_info = data.get("copyright", "Public Domain")

                        embed = discord.Embed(
                            title=f"🌌 {title}",
                            description=f"**{date}**\n\n{explanation[:3500]}...", # Limit description length if needed
                            color=discord.Color.dark_blue()
                        )
                        
                        if media_url:
                            embed.set_image(url=media_url)
                        
                        embed.set_footer(text=f"© {copyright_info} | Source: NASA APOD")
                        
                        if hd_url:
                            embed.add_field(name="HD Image", value=f"[Click Here]({hd_url})", inline=False)

                        await interaction.followup.send(embed=embed)
                    elif response.status == 429:
                        await interaction.followup.send("❌ NASA API rate limit exceeded. Please try again later.", ephemeral=True)
                    else:
                        await interaction.followup.send(f"❌ Failed to fetch APOD. (Status: {response.status})", ephemeral=True)
            except Exception as e:
                await interaction.followup.send(f"❌ An error occurred: {str(e)}", ephemeral=True)

    @app_commands.command(name="iss", description="Get the current location of the International Space Station")
    async def iss(self, interaction: discord.Interaction):
        """Shows the current location of the ISS."""
        await interaction.response.defer()
        
        url = "http://api.open-notify.org/iss-now.json"

        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        position = data.get("iss_position", {})
                        lat = position.get("latitude")
                        lon = position.get("longitude")
                        timestamp = data.get("timestamp")

                        if lat and lon:
                            maps_url = f"https://www.google.com/maps/search/?api=1&query={lat},{lon}"
                            
                            embed = discord.Embed(
                                title="🛰️ ISS Live Location",
                                description=f"The International Space Station is currently over:",
                                color=discord.Color.red()
                            )
                            embed.add_field(name="Latitude", value=lat, inline=True)
                            embed.add_field(name="Longitude", value=lon, inline=True)
                            embed.add_field(name="Visualization", value=f"[View on Google Maps]({maps_url})", inline=False)
                            embed.set_footer(text=f"Updated: <t:{timestamp}:R>")
                            
                            await interaction.followup.send(embed=embed)
                        else:
                             await interaction.followup.send("❌ Could not retrieve coordinates.", ephemeral=True)

                    else:
                        await interaction.followup.send(f"❌ Failed to fetch ISS location. (Status: {response.status})", ephemeral=True)
            except Exception as e:
                await interaction.followup.send(f"❌ An error occurred: {str(e)}", ephemeral=True)

    @app_commands.command(name="astronauts", description="See who is currently in space")
    async def astronauts(self, interaction: discord.Interaction):
        """Lists all humans currently in space."""
        await interaction.response.defer()
        
        url = "http://api.open-notify.org/astros.json"

        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        number = data.get("number", 0)
                        people = data.get("people", [])

                        embed = discord.Embed(
                            title=f"🧑‍🚀 People in Space: {number}",
                            color=discord.Color.gold()
                        )

                        # Group by craft
                        crafts = {}
                        for person in people:
                            craft = person['craft']
                            name = person['name']
                            if craft not in crafts:
                                crafts[craft] = []
                            crafts[craft].append(name)

                        for craft, names in crafts.items():
                            embed.add_field(name=f"🚀 {craft}", value="\n".join(f"• {name}" for name in names), inline=False)

                        await interaction.followup.send(embed=embed)
                    else:
                         await interaction.followup.send(f"❌ Failed to fetch people in space. (Status: {response.status})", ephemeral=True)
            except Exception as e:
                 await interaction.followup.send(f"❌ An error occurred: {str(e)}", ephemeral=True)


    @app_commands.command(name="launch", description="Get info on the next rocket launch")
    async def launch(self, interaction: discord.Interaction):
        """Shows the next upcoming rocket launch."""
        await interaction.response.defer()

        # Cache check
        current_time = time.time()
        if self.launch_cache and (current_time - self.launch_cache_time < self.LAUNCH_CACHE_DURATION):
             await interaction.followup.send(embed=self.launch_cache)
             return

        url = "https://ll.thespacedevs.com/2.2.0/launch/upcoming/?limit=1"

        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        results = data.get("results", [])
                        
                        if not results:
                            await interaction.followup.send("❌ No upcoming launches found.", ephemeral=True)
                            return

                        launch = results[0]
                        name = launch.get("name", "Unknown Mission")
                        status = launch.get("status", {}).get("name", "Unknown Status")
                        description = launch.get("mission", {}).get("description")
                        if not description:
                             description = "No description available."
                        
                        # Provider
                        provider = launch.get("launch_service_provider", {}).get("name", "Unknown Provider")
                        
                        # Pad
                        pad_name = launch.get("pad", {}).get("name", "Unknown Pad")
                        location = launch.get("pad", {}).get("location", {}).get("name", "Unknown Location")

                        # Image
                        image_url = launch.get("image")

                        # Net Launch Time
                        net = launch.get("net")
                        # Parse ISO string to timestamp
                        try:
                            dt = datetime.datetime.fromisoformat(net.replace("Z", "+00:00"))
                            timestamp = int(dt.timestamp())
                            time_str = f"<t:{timestamp}:F> (<t:{timestamp}:R>)"
                        except:
                            time_str = net

                        embed = discord.Embed(
                            title=f"🚀 Next Launch: {name}",
                            description=description[:4000],
                            color=discord.Color.purple()
                        )
                        
                        embed.add_field(name="Provider", value=provider, inline=True)
                        embed.add_field(name="Status", value=status, inline=True)
                        embed.add_field(name="Launch Time", value=time_str, inline=False)
                        embed.add_field(name="Location", value=f"{pad_name}, {location}", inline=False)
                        
                        if image_url:
                            embed.set_thumbnail(url=image_url)
                        
                        embed.set_footer(text="Data provided by The Space Devs")

                        # Update Cache
                        self.launch_cache = embed
                        self.launch_cache_time = current_time

                        await interaction.followup.send(embed=embed)
                    
                    elif response.status == 429:
                         await interaction.followup.send("❌ Launch API rate limit exceeded. Please wait a while.", ephemeral=True)
                    else:
                         await interaction.followup.send(f"❌ Failed to fetch launch data. (Status: {response.status})", ephemeral=True)

            except Exception as e:
                await interaction.followup.send(f"❌ An error occurred: {str(e)}", ephemeral=True)


async def setup(bot):
    await bot.add_cog(Cosmos(bot))
    print("Cosmos cog loaded successfully")


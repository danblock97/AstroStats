import discord
from discord.ext import commands
from discord import app_commands
import aiohttp
import os
import datetime
import time
import random

class Cosmos(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.launch_cache = None
        self.launch_cache_time = 0
        self.LAUNCH_CACHE_DURATION = 900  # 15 minutes in seconds
        self.geocode_cache = {}
        self.GEOCODE_CACHE_DURATION = 6 * 60 * 60  # 6 hours
        self.spacefact_cache = None
        self.spacefact_cache_time = 0
        self.SPACEFACT_CACHE_DURATION = 300  # 5 minutes

    async def _geocode_city(self, session: aiohttp.ClientSession, city: str, country: str | None = None):
        """Resolve a city name to latitude/longitude using Nominatim."""
        normalized = f"{city.strip().lower()}|{(country or '').strip().lower()}"
        cached = self.geocode_cache.get(normalized)
        if cached and (time.time() - cached["timestamp"] < self.GEOCODE_CACHE_DURATION):
            return cached["data"]

        url = "https://nominatim.openstreetmap.org/search"
        query = f"{city}, {country}" if country else city
        params = {
            "q": query,
            "format": "jsonv2",
            "limit": 5,
            "addressdetails": 1
        }
        headers = {"User-Agent": "AstroStatsBot/1.0 (https://astrostats.info)"}

        async with session.get(url, params=params, headers=headers) as response:
            if response.status != 200:
                return None
            data = await response.json()
            if not data:
                return None

            entry = None
            if country:
                country_normalized = country.strip().lower()
                for candidate in data:
                    address = candidate.get("address", {})
                    if address.get("country_code", "").lower() == country_normalized:
                        entry = candidate
                        break
                    if address.get("country", "").lower() == country_normalized:
                        entry = candidate
                        break
            if entry is None:
                entry = data[0]
            location = {
                "lat": float(entry["lat"]),
                "lon": float(entry["lon"]),
                "display_name": entry.get("display_name", query)
            }

        self.geocode_cache[normalized] = {
            "timestamp": time.time(),
            "data": location
        }
        return location

    def _extract_fact(self, explanation: str) -> str:
        """Extract a concise fact from APOD explanation text."""
        if not explanation:
            return "No fact available."
        cleaned = " ".join(explanation.split())
        sentences = [s.strip() for s in cleaned.split(". ") if s.strip()]
        fact = ". ".join(sentences[:2])
        if fact and not fact.endswith("."):
            fact += "."
        return fact[:1000]

    def _azimuth_to_compass(self, azimuth: float) -> str:
        """Convert azimuth degrees to a compass direction."""
        directions = [
            "N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
            "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"
        ]
        idx = int((azimuth % 360) / 22.5 + 0.5) % 16
        return directions[idx]

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

    @app_commands.command(name="iss-pass", description="Get upcoming ISS pass times for a city")
    @app_commands.describe(city="City name, e.g., Bristol", country="Optional country, e.g., UK")
    async def iss_pass(self, interaction: discord.Interaction, city: str, country: str | None = None):
        """Shows upcoming ISS pass times for a given city."""
        await interaction.response.defer()

        async with aiohttp.ClientSession() as session:
            try:
                location = await self._geocode_city(session, city, country)
                if not location:
                    await interaction.followup.send(
                        "❌ Could not find that city. Try a more specific name (e.g., 'Bristol, UK').",
                        ephemeral=True
                    )
                    return

                lat = location["lat"]
                lon = location["lon"]
                api_key = os.getenv("N2YO_API_KEY")
                if not api_key:
                    await interaction.followup.send(
                        "❌ N2YO API key is not configured. Please set N2YO_API_KEY.",
                        ephemeral=True
                    )
                    return

                url = (
                    f"https://api.n2yo.com/rest/v1/satellite/visualpasses/"
                    f"25544/{lat}/{lon}/0/2/30/"
                )
                params = {"apiKey": api_key}

                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                    elif response.status == 429:
                        await interaction.followup.send(
                            "❌ ISS pass API rate limit exceeded. Please try again later.",
                            ephemeral=True
                        )
                        return
                    else:
                        await interaction.followup.send(
                            f"❌ Failed to fetch ISS pass data. (Status: {response.status})",
                            ephemeral=True
                        )
                        return

                passes = data.get("passes", [])
                if not passes:
                    await interaction.followup.send(
                        "❌ No upcoming passes found for this location.",
                        ephemeral=True
                    )
                    return

                embed = discord.Embed(
                    title="🛰️ Upcoming ISS Passes",
                    description=f"Location: **{location['display_name']}**",
                    color=discord.Color.blue()
                )

                pass_lines = []
                for entry in passes[:5]:
                    risetime = entry.get("startUTC")
                    duration = entry.get("duration", 0)
                    minutes = duration // 60
                    seconds = duration % 60
                    duration_str = f"{minutes}m {seconds}s" if minutes else f"{seconds}s"
                    start_az = entry.get("startAz")
                    max_az = entry.get("maxAz")
                    end_az = entry.get("endAz")
                    max_el = entry.get("maxEl")

                    direction_bits = []
                    if start_az is not None and end_az is not None:
                        start_dir = self._azimuth_to_compass(float(start_az))
                        end_dir = self._azimuth_to_compass(float(end_az))
                        direction_bits.append(f"{start_dir}→{end_dir}")
                    if max_el is not None:
                        direction_bits.append(f"max {int(max_el)}°")
                    direction_text = f" ({', '.join(direction_bits)})" if direction_bits else ""
                    if risetime:
                        pass_lines.append(
                            f"• <t:{risetime}:F> (<t:{risetime}:R>) — **visible for {duration_str}**{direction_text}"
                        )

                maps_url = f"https://www.google.com/maps/search/?api=1&query={lat},{lon}"
                embed.add_field(
                    name="Next Passes",
                    value="\n".join(pass_lines),
                    inline=False
                )
                embed.add_field(
                    name="What does duration mean?",
                    value="Approximate time the ISS is visible above the horizon for this location.",
                    inline=False
                )
                embed.add_field(
                    name="How to look",
                    value="Directions show where the ISS starts and ends (compass), plus max elevation.",
                    inline=False
                )
                embed.add_field(
                    name="Map",
                    value=f"[View location]({maps_url})",
                    inline=False
                )
                embed.set_footer(text="Data provided by N2YO")

                await interaction.followup.send(embed=embed)
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

    @app_commands.command(name="spacefact", description="Get a random space fact")
    async def spacefact(self, interaction: discord.Interaction):
        """Shows a random space fact using NASA APOD data."""
        await interaction.response.defer()

        current_time = time.time()
        if self.spacefact_cache and (current_time - self.spacefact_cache_time < self.SPACEFACT_CACHE_DURATION):
            await interaction.followup.send(embed=self.spacefact_cache)
            return

        api_key = os.getenv("NASA_API_KEY", "DEMO_KEY")
        end_date = datetime.date.today()
        start_date = end_date - datetime.timedelta(days=365 * 10)
        random_days = random.randint(0, (end_date - start_date).days)
        random_date = start_date + datetime.timedelta(days=random_days)

        url = f"https://api.nasa.gov/planetary/apod?api_key={api_key}&date={random_date.isoformat()}"

        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        explanation = data.get("explanation", "")
                        fact = self._extract_fact(explanation)
                        title = data.get("title", "Space Fact")
                        date = data.get("date", random_date.isoformat())
                        media_type = data.get("media_type", "image")
                        media_url = data.get("url")

                        embed = discord.Embed(
                            title=f"🪐 {title}",
                            description=fact,
                            color=discord.Color.dark_blue()
                        )
                        embed.add_field(name="Date", value=date, inline=True)
                        if media_url:
                            embed.add_field(name="Source", value=f"[NASA APOD]({media_url})", inline=True)
                        if media_type == "image" and media_url:
                            embed.set_image(url=media_url)
                        embed.set_footer(text="Data provided by NASA APOD")

                        self.spacefact_cache = embed
                        self.spacefact_cache_time = current_time

                        await interaction.followup.send(embed=embed)
                    elif response.status == 429:
                        await interaction.followup.send(
                            "❌ NASA API rate limit exceeded. Please try again later.",
                            ephemeral=True
                        )
                    else:
                        await interaction.followup.send(
                            f"❌ Failed to fetch space fact. (Status: {response.status})",
                            ephemeral=True
                        )
            except Exception as e:
                await interaction.followup.send(f"❌ An error occurred: {str(e)}", ephemeral=True)


async def setup(bot):
    await bot.add_cog(Cosmos(bot))
    print("Cosmos cog loaded successfully")


# cogs/general/statuspage.py
import logging
import asyncio
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Tuple

import aiohttp
import discord
from discord.ext import commands, tasks
from discord import app_commands

from config.settings import STATUSPAGE_API_BASE, STATUSPAGE_API_KEY
from services.database.statuspage import (
    get_statuspage_settings,
    update_statuspage_settings,
    get_all_enabled_guilds,
)

logger = logging.getLogger(__name__)

POLL_INTERVAL_MINUTES = 5
MAX_DEDUPE_IDS = 200
FETCH_RETRIES = 3
FETCH_RETRY_BASE_DELAY_SECONDS = 2

MOCK_INCIDENT = {
    "id": "mock_incident_1",
    "name": "AstroStats API Degraded",
    "impact": "major",
    "status": "identified",
    "shortlink": "https://astrostats.statuspage.io/incidents/mock",
    "components": [
        {"name": "Core Bot"},
        {"name": "Game Stats APIs"},
    ],
}

MOCK_UPDATE = {
    "id": "mock_update_1",
    "status": "identified",
    "body": "We are investigating elevated error rates for API requests. A fix is in progress.",
    "updated_at": "2026-02-03T20:30:00Z",
}


def _parse_iso(ts: Optional[str]) -> Optional[datetime]:
    if not ts:
        return None
    try:
        if ts.endswith("Z"):
            ts = ts[:-1] + "+00:00"
        return datetime.fromisoformat(ts)
    except Exception:
        return None


def _impact_color(impact: str) -> discord.Color:
    impact_norm = (impact or "").lower()
    if impact_norm in {"critical", "major"}:
        return discord.Color.red()
    if impact_norm in {"minor"}:
        return discord.Color.orange()
    if impact_norm in {"maintenance"}:
        return discord.Color.blue()
    return discord.Color.gold()


def _status_color(status: str, impact: str) -> discord.Color:
    status_norm = (status or "").lower()
    if status_norm == "investigating":
        return discord.Color.red()
    if status_norm == "identified":
        return discord.Color.orange()
    if status_norm == "monitoring":
        return discord.Color.gold()
    if status_norm == "resolved":
        return discord.Color.green()
    return _impact_color(impact)


def _truncate(text: str, limit: int = 3500) -> str:
    if text is None:
        return ""
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


class StatusPageCog(commands.GroupCog, group_name="statuspage"):
    """Statuspage incident updates for servers."""

    def __init__(self, bot: commands.Bot):
        super().__init__()
        self.bot = bot
        self.poll_statuspage.start()

    def _auth_headers(self) -> Dict[str, str]:
        if STATUSPAGE_API_KEY:
            return {"Authorization": STATUSPAGE_API_KEY}
        return {}

    async def _fetch_statuspage_list(self, endpoint: str, root_key: str, label: str) -> List[Dict[str, Any]]:
        if not STATUSPAGE_API_BASE:
            logger.warning("STATUSPAGE_API_BASE is not set; skipping statuspage polling.")
            return []
        url = f"{STATUSPAGE_API_BASE}/{endpoint}"
        for attempt in range(1, FETCH_RETRIES + 1):
            async with aiohttp.ClientSession() as session:
                try:
                    async with session.get(url, headers=self._auth_headers()) as response:
                        if response.status == 200:
                            data = await response.json()
                            items = data.get(root_key, [])
                            if isinstance(items, list):
                                return items
                            return []

                        should_retry = response.status >= 500 or response.status in {429}
                        logger.warning(
                            "Statuspage %s fetch failed: HTTP %s (attempt %s/%s)",
                            label,
                            response.status,
                            attempt,
                            FETCH_RETRIES,
                        )
                        if not should_retry or attempt == FETCH_RETRIES:
                            return []
                except Exception as e:
                    logger.warning(
                        "Statuspage %s fetch error on attempt %s/%s: %s",
                        label,
                        attempt,
                        FETCH_RETRIES,
                        e,
                    )
                    if attempt == FETCH_RETRIES:
                        logger.error("Statuspage %s fetch error: %s", label, e, exc_info=True)
                        return []

            await asyncio.sleep(FETCH_RETRY_BASE_DELAY_SECONDS * attempt)
        return []

    async def fetch_incidents(self) -> List[Dict[str, Any]]:
        return await self._fetch_statuspage_list(
            endpoint="incidents.json",
            root_key="incidents",
            label="incidents",
        )

    async def fetch_maintenances(self) -> List[Dict[str, Any]]:
        return await self._fetch_statuspage_list(
            endpoint="scheduled-maintenances.json",
            root_key="scheduled_maintenances",
            label="maintenances",
        )

    def _stable_update_id(self, record: Dict[str, Any], update: Dict[str, Any], kind: str) -> str:
        update_id = update.get("id")
        if update_id:
            return str(update_id)

        parent_id = str(record.get("id") or "unknown")
        status = str(update.get("status") or record.get("status") or "unknown").lower()
        timestamp = (
            update.get("updated_at")
            or update.get("created_at")
            or record.get("updated_at")
            or record.get("scheduled_for")
            or record.get("created_at")
            or "unknown"
        )
        return f"{kind}:{parent_id}:{status}:{timestamp}"

    def _collect_updates(
        self,
        incidents: List[Dict[str, Any]],
        maintenances: Optional[List[Dict[str, Any]]] = None,
    ) -> List[Tuple[datetime, Dict[str, Any], Dict[str, Any], str]]:
        updates: List[Tuple[datetime, Dict[str, Any], Dict[str, Any], str]] = []
        for incident in incidents:
            for update in incident.get("incident_updates", []) or []:
                update_payload = dict(update or {})
                update_payload["id"] = self._stable_update_id(incident, update_payload, "incident")
                ts = _parse_iso(update_payload.get("updated_at")) or _parse_iso(update_payload.get("created_at")) or datetime.now(timezone.utc)
                updates.append((ts, incident, update_payload, "incident"))
        for maintenance in maintenances or []:
            status_norm = (maintenance.get("status") or "").lower()

            scheduled_for = _parse_iso(maintenance.get("scheduled_for"))
            if scheduled_for and scheduled_for < datetime.now(timezone.utc) and status_norm not in {"in_progress", "verifying", "completed", "resolved"}:
                continue

            maintenance_updates = (
                maintenance.get("scheduled_maintenance_updates")
                or maintenance.get("incident_updates")
                or []
            )
            if maintenance_updates:
                for update in maintenance_updates:
                    update_payload = dict(update or {})
                    update_payload["id"] = self._stable_update_id(maintenance, update_payload, "maintenance")
                    ts = _parse_iso(update_payload.get("updated_at")) or _parse_iso(update_payload.get("created_at")) or scheduled_for or datetime.now(timezone.utc)
                    updates.append((ts, maintenance, update_payload, "maintenance"))
            else:
                fallback_id = maintenance.get("id")
                fallback_status = maintenance.get("status") or "scheduled"
                update = {
                    "id": f"{fallback_id}:{fallback_status}" if fallback_id else None,
                    "status": fallback_status,
                    "body": maintenance.get("incident_description") or maintenance.get("name") or "Scheduled maintenance.",
                    "updated_at": maintenance.get("updated_at") or maintenance.get("scheduled_for"),
                    "created_at": maintenance.get("created_at") or maintenance.get("scheduled_for"),
                }
                update["id"] = self._stable_update_id(maintenance, update, "maintenance")
                ts = _parse_iso(update.get("updated_at")) or _parse_iso(update.get("created_at")) or datetime.now(timezone.utc)
                updates.append((ts, maintenance, update, "maintenance"))
        updates.sort(key=lambda x: x[0])
        return updates

    def _build_embed(self, incident: Dict[str, Any], update: Dict[str, Any], kind: str = "incident") -> discord.Embed:
        name = incident.get("name") or "Incident Update"
        body = _truncate(update.get("body", ""))
        is_maintenance = kind == "maintenance" or bool(incident.get("scheduled_for") or incident.get("scheduled_until"))
        impact = incident.get("impact", "") or ("maintenance" if is_maintenance else "")
        status = update.get("status") or incident.get("status", "unknown")

        embed = discord.Embed(
            title=name,
            description=body,
            color=_status_color(status, impact),
            timestamp=_parse_iso(update.get("updated_at")) or datetime.now(timezone.utc)
        )
        embed.add_field(name="Status", value=str(status).replace("_", " ").title(), inline=True)
        embed.add_field(name="Impact", value=str(impact or "none").replace("_", " ").title(), inline=True)

        if is_maintenance:
            scheduled_for = _parse_iso(incident.get("scheduled_for"))
            scheduled_until = _parse_iso(incident.get("scheduled_until"))
            if scheduled_for:
                embed.add_field(name="Scheduled For", value=f"<t:{int(scheduled_for.timestamp())}:f>", inline=True)
            if scheduled_until:
                embed.add_field(name="Scheduled Until", value=f"<t:{int(scheduled_until.timestamp())}:f>", inline=True)

        components = incident.get("components", [])
        if isinstance(components, list) and components:
            names = ", ".join([c.get("name") for c in components if c.get("name")])[:1000]
            if names:
                embed.add_field(name="Affected", value=names, inline=False)

        url = incident.get("shortlink") or incident.get("url")
        if url:
            label = "View maintenance" if is_maintenance else "View incident"
            embed.add_field(name=label, value=url, inline=False)

        embed.set_footer(text="AstroStats Status")
        return embed

    async def _post_updates_for_guild(
        self,
        guild_doc: Dict[str, Any],
        updates: List[Tuple[datetime, Dict[str, Any], Dict[str, Any], str]],
    ) -> None:
        guild_id = guild_doc.get("guild_id")
        channel_id = guild_doc.get("channel_id")
        if not guild_id or not channel_id:
            return

        guild = self.bot.get_guild(int(guild_id))
        if not guild:
            return

        channel = guild.get_channel(int(channel_id))
        if not isinstance(channel, discord.TextChannel):
            return

        me = guild.me or guild.get_member(self.bot.user.id)
        if not me or not channel.permissions_for(me).send_messages:
            logger.warning("Missing send permissions for statuspage channel %s in guild %s", channel_id, guild_id)
            return

        settings = get_statuspage_settings(str(guild_id))
        last_ids = settings.last_posted_update_ids if settings else []

        new_updates: List[Tuple[datetime, Dict[str, Any], Dict[str, Any], str]] = []
        for ts, incident, update, kind in updates:
            update_id = update.get("id")
            if update_id and update_id not in last_ids:
                new_updates.append((ts, incident, update, kind))

        if not new_updates:
            return

        for _, incident, update, kind in new_updates:
            embed = self._build_embed(incident, update, kind)
            try:
                await channel.send(embed=embed)
            except Exception as e:
                logger.error("Failed to send statuspage update to %s: %s", channel_id, e, exc_info=True)

        # Update de-dupe list
        for _, _, update, _ in new_updates:
            update_id = update.get("id")
            if update_id:
                last_ids.append(update_id)

        last_ids = last_ids[-MAX_DEDUPE_IDS:]
        update_statuspage_settings(str(guild_id), last_posted_update_ids=last_ids)

    @tasks.loop(minutes=POLL_INTERVAL_MINUTES)
    async def poll_statuspage(self):
        try:
            enabled_guilds = get_all_enabled_guilds()
            if not enabled_guilds:
                return

            incidents = await self.fetch_incidents()
            maintenances = await self.fetch_maintenances()
            if not incidents and not maintenances:
                return

            updates = self._collect_updates(incidents, maintenances)
            if not updates:
                return

            for guild_doc in enabled_guilds:
                await self._post_updates_for_guild(guild_doc, updates)
        except Exception as e:
            logger.error("Statuspage poll loop error: %s", e, exc_info=True)

    @poll_statuspage.before_loop
    async def before_poll_statuspage(self):
        await self.bot.wait_until_ready()

    def cog_unload(self):
        self.poll_statuspage.cancel()

    async def _has_manage_guild(self, interaction: discord.Interaction) -> bool:
        if not interaction.guild:
            await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)
            return False
        if not interaction.user.guild_permissions.manage_guild:
            embed = discord.Embed(
                title="❌ Missing Permissions",
                description="You need the **Manage Server** permission to use this command.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return False
        return True

    @app_commands.command(name="enable", description="Enable AstroStats status updates in a channel")
    @app_commands.describe(channel="Channel to post incident updates")
    async def enable(self, interaction: discord.Interaction, channel: discord.TextChannel):
        if not await self._has_manage_guild(interaction):
            return

        me = interaction.guild.me or interaction.guild.get_member(self.bot.user.id)
        if not me or not channel.permissions_for(me).send_messages:
            await interaction.response.send_message(
                "I don't have permission to send messages in that channel.",
                ephemeral=True
            )
            return

        guild_id = str(interaction.guild.id)
        channel_id = str(channel.id)

        # Prime de-dupe list with current updates to avoid backfill spam
        incidents = await self.fetch_incidents()
        maintenances = await self.fetch_maintenances()
        updates = self._collect_updates(incidents, maintenances)
        existing_ids = [u.get("id") for _, _, u, _ in updates if u.get("id")]
        existing_ids = existing_ids[-MAX_DEDUPE_IDS:]

        success = update_statuspage_settings(
            guild_id=guild_id,
            enabled=True,
            channel_id=channel_id,
            last_posted_update_ids=existing_ids
        )

        if not success:
            await interaction.response.send_message("Failed to enable status updates. Please try again.", ephemeral=True)
            return

        embed = discord.Embed(
            title="✅ Status Updates Enabled",
            description=f"Incidents will be posted in {channel.mention}.",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="disable", description="Disable AstroStats status updates")
    async def disable(self, interaction: discord.Interaction):
        if not await self._has_manage_guild(interaction):
            return

        guild_id = str(interaction.guild.id)
        success = update_statuspage_settings(guild_id=guild_id, enabled=False)
        if not success:
            await interaction.response.send_message("Failed to disable status updates. Please try again.", ephemeral=True)
            return

        embed = discord.Embed(
            title="❌ Status Updates Disabled",
            description="AstroStats status updates are now disabled for this server.",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="test", description="Send a sample status update embed")
    @app_commands.describe(channel="Channel to post the test embed (defaults to current)")
    async def test(self, interaction: discord.Interaction, channel: Optional[discord.TextChannel] = None):
        if not await self._has_manage_guild(interaction):
            return

        target = channel or interaction.channel
        if not isinstance(target, discord.TextChannel):
            await interaction.response.send_message("Please choose a text channel.", ephemeral=True)
            return

        me = interaction.guild.me or interaction.guild.get_member(self.bot.user.id)
        if not me or not target.permissions_for(me).send_messages:
            await interaction.response.send_message(
                "I don't have permission to send messages in that channel.",
                ephemeral=True
            )
            return

        embed = self._build_embed(MOCK_INCIDENT, MOCK_UPDATE)
        await target.send(embed=embed)
        await interaction.response.send_message(
            f"Sent a test status update to {target.mention}.",
            ephemeral=True
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(StatusPageCog(bot))

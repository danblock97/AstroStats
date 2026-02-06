from unittest.mock import MagicMock, AsyncMock

import pytest

from cogs.general.statuspage import StatusPageCog
import cogs.general.statuspage as statuspage_module


def _make_cog() -> StatusPageCog:
    cog = StatusPageCog.__new__(StatusPageCog)
    cog.bot = MagicMock()
    return cog


def test_collect_updates_includes_completed_maintenance_updates():
    cog = _make_cog()
    maintenances = [
        {
            "id": "maint_1",
            "name": "Scheduled deploy",
            "status": "completed",
            "scheduled_for": "2026-02-05T14:00:00Z",
            "scheduled_maintenance_updates": [
                {
                    "id": "maint_update_1",
                    "status": "completed",
                    "body": "Maintenance completed successfully.",
                    "updated_at": "2026-02-05T14:20:00Z",
                }
            ],
        }
    ]

    updates = cog._collect_updates([], maintenances)

    assert len(updates) == 1
    _, _, update, kind = updates[0]
    assert kind == "maintenance"
    assert update["id"] == "maint_update_1"
    assert update["status"] == "completed"


def test_collect_updates_uses_status_specific_fallback_ids():
    cog = _make_cog()
    maintenances = [
        {
            "id": "maint_2",
            "name": "Phase 1",
            "status": "scheduled",
            "scheduled_for": "2099-02-05T14:00:00Z",
            "updated_at": "2026-02-05T13:40:00Z",
            "scheduled_maintenance_updates": [],
        },
        {
            "id": "maint_2",
            "name": "Phase 2",
            "status": "completed",
            "scheduled_for": "2026-02-05T14:00:00Z",
            "updated_at": "2026-02-05T14:20:00Z",
            "scheduled_maintenance_updates": [],
        },
    ]

    updates = cog._collect_updates([], maintenances)
    update_ids = [update["id"] for _, _, update, _ in updates]

    assert "maint_2:scheduled" in update_ids
    assert "maint_2:completed" in update_ids


def test_collect_updates_generates_stable_id_when_missing():
    cog = _make_cog()
    maintenances = [
        {
            "id": "maint_3",
            "name": "Deploy",
            "status": "completed",
            "scheduled_for": "2026-02-05T14:00:00Z",
            "scheduled_maintenance_updates": [
                {
                    "status": "completed",
                    "body": "Done",
                    "updated_at": "2026-02-05T14:20:00Z",
                }
            ],
        }
    ]

    updates = cog._collect_updates([], maintenances)
    _, _, update, kind = updates[0]

    assert kind == "maintenance"
    assert update["id"] == "maintenance:maint_3:completed:2026-02-05T14:20:00Z"


class _FakeResponse:
    def __init__(self, status: int, payload: dict):
        self.status = status
        self._payload = payload

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def json(self):
        return self._payload


class _FakeSession:
    def __init__(self, status: int, payload: dict):
        self._status = status
        self._payload = payload

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    def get(self, url, headers=None):  # noqa: ARG002
        return _FakeResponse(self._status, self._payload)


@pytest.mark.asyncio
async def test_fetch_maintenances_retries_after_503_and_recovers(monkeypatch):
    cog = _make_cog()
    attempts = {"count": 0}

    def fake_client_session(*args, **kwargs):  # noqa: ARG001, ARG002
        attempts["count"] += 1
        if attempts["count"] == 1:
            return _FakeSession(503, {})
        return _FakeSession(200, {"scheduled_maintenances": [{"id": "maint_4"}]})

    sleep_mock = AsyncMock()

    monkeypatch.setattr(statuspage_module, "STATUSPAGE_API_BASE", "https://example.statuspage.io/api/v2")
    monkeypatch.setattr(statuspage_module.aiohttp, "ClientSession", fake_client_session)
    monkeypatch.setattr(statuspage_module.asyncio, "sleep", sleep_mock)

    maintenances = await cog.fetch_maintenances()

    assert maintenances == [{"id": "maint_4"}]
    assert attempts["count"] == 2
    sleep_mock.assert_awaited_once_with(statuspage_module.FETCH_RETRY_BASE_DELAY_SECONDS)

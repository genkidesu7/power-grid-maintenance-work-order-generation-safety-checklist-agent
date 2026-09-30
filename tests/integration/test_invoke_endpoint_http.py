# Regression test (test_rule.md Rule 3): agent.invoke() is sync and its
# inner nodes call asyncio.run() internally. Calling it directly from an
# async route (without asyncio.to_thread) raises "asyncio.run() cannot be
# called from a running event loop" inside the node, which the node's
# except-Exception silently turns into status: "error" — a 200 response
# with no visible crash. An in-process sync call to agent.invoke() never
# exercises this path; only a real ASGI transport does, because only that
# puts the call inside a running event loop.

import json
import secrets

import pytest
from httpx import ASGITransport, AsyncClient


@pytest.mark.asyncio
async def test_invoke_endpoint_succeeds_over_http(monkeypatch):
    monkeypatch.setenv("USE_MOCK", "true")
    token = secrets.token_urlsafe(32)
    monkeypatch.setenv("INVOKE_AUTH_TOKEN", token)

    # Import after env is set so the module-level `agent` picks up USE_MOCK
    # for any state that depends on it at import time; the app itself reads
    # INVOKE_AUTH_TOKEN per-request via os.environ, not at import time.
    from src.api.server import app

    body = json.dumps(
        {
            "work_type": "transformer_replacement",
            "equipment_id": "TR-1024",
            "location": "Site A",
            "schedule": "2026-08-01T09:00:00",
            "crew_size": 4,
        }
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/invoke",
            json={"input": body},
            headers={"Authorization": f"Bearer {token}"},
        )

    assert resp.status_code == 200
    payload = resp.json()
    assert payload["status"] == "success", (
        f"invoke over a real ASGI transport returned status={payload['status']!r} — "
        "this is the asyncio.run()-inside-running-loop bug if it recurs "
        "(.claude/rules/implementation_rule.md Rule 3)"
    )
    assert payload["output"]["work_order"]["equipment_id"] == "TR-1024"


@pytest.mark.asyncio
async def test_invoke_endpoint_rejects_missing_bearer_token(monkeypatch):
    monkeypatch.setenv("USE_MOCK", "true")
    monkeypatch.setenv("INVOKE_AUTH_TOKEN", secrets.token_urlsafe(32))

    from src.api.server import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/invoke", json={"input": "{}"})

    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_health_endpoint():
    from src.api.server import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/health")

    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"

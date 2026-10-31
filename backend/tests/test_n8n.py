"""Tests for n8n service — graceful handling of unreachable / unconfigured n8n."""
import asyncio

from app.services.n8n_service import N8nService
from app.config import Settings


def test_no_webhook_returns_skipped():
    s = Settings(n8n_webhook_url=None)
    svc = N8nService(settings=s)
    out = asyncio.get_event_loop().run_until_complete(svc.submit_exorcism({"ping": "x"}))
    assert out["submitted"] is False
    assert out["workflow_status"] == "skipped"


def test_unreachable_n8n_does_not_raise():
    s = Settings(n8n_webhook_url="http://127.0.0.1:65535/nope")
    svc = N8nService(settings=s)
    out = asyncio.get_event_loop().run_until_complete(svc.submit_exorcism({"ping": "x"}))
    assert out["submitted"] is False
    # Either unreachable or error — both are non-raising
    assert out["workflow_status"] in ("unreachable", "error", "skipped")


def test_test_connection_returns_false_when_unconfigured():
    s = Settings(n8n_webhook_url=None)
    svc = N8nService(settings=s)
    out = asyncio.get_event_loop().run_until_complete(svc.test_connection())
    assert out["connected"] is False
    assert "N8N_WEBHOOK_URL" in out["detail"]

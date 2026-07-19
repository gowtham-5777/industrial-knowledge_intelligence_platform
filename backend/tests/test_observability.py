"""Tests for Milestone 1.10 — logging & observability foundation."""

from __future__ import annotations

import json
import logging
from io import StringIO

import pytest
from app.core.config import Settings, clear_settings_cache
from app.db.session import clear_engine_cache
from app.main import create_app
from app.observability import (
    clear_context,
    get_logger,
    get_request_id,
    get_request_metrics,
    reset_logging_state,
    set_job_id,
    set_request_id,
)
from app.observability.logging import JsonFormatter
from fastapi.testclient import TestClient


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("LOG_JSON", "true")
    monkeypatch.setenv("LOG_LEVEL", "INFO")
    clear_settings_cache()
    clear_engine_cache()
    reset_logging_state()
    get_request_metrics().reset()
    clear_context()
    app = create_app(
        Settings(
            app_env="test",
            database_url="sqlite:///:memory:",
            log_json=True,
            log_level="INFO",
        )
    )
    with TestClient(app) as test_client:
        yield test_client
    get_request_metrics().reset()
    clear_context()
    clear_settings_cache()
    clear_engine_cache()
    reset_logging_state()


def test_json_formatter_includes_request_id() -> None:
    reset_logging_state()
    clear_context()
    set_request_id("corr-abc-123")
    set_job_id("job-9")

    stream = StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(JsonFormatter())
    logger = get_logger("app.observability.test")
    logger.handlers.clear()
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False

    logger.info("pipeline stage", extra={"stage": "discovery"})
    handler.flush()
    clear_context()

    line = stream.getvalue().strip()
    payload = json.loads(line)
    assert payload["level"] == "INFO"
    assert payload["message"] == "pipeline stage"
    assert payload["request_id"] == "corr-abc-123"
    assert payload["job_id"] == "job-9"
    assert payload["module"]
    assert payload["logger"] == "app.observability.test"
    assert payload["stage"] == "discovery"
    assert "timestamp" in payload


def test_access_log_is_json_with_request_id(
    client: TestClient, caplog: pytest.LogCaptureFixture
) -> None:
    access = logging.getLogger("app.access")
    access.setLevel(logging.INFO)
    access.disabled = False

    with caplog.at_level(logging.INFO, logger="app.access"):
        response = client.get("/health", headers={"X-Request-ID": "log-req-42"})

    assert response.status_code == 200
    records = [
        r
        for r in caplog.records
        if r.name == "app.access" and r.getMessage() == "request completed"
    ]
    assert records, "expected access log for completed request"
    payload = json.loads(JsonFormatter().format(records[-1]))
    assert payload["message"] == "request completed"
    assert payload["request_id"] == "log-req-42"
    assert payload["http_method"] == "GET"
    assert payload["http_path"] == "/health"
    assert payload["http_status"] == 200
    assert "latency_ms" in payload


def test_request_metrics_latency_counters(client: TestClient) -> None:
    metrics = get_request_metrics()
    metrics.reset()
    before = metrics.snapshot()["request_count"]

    client.get("/health")
    client.get("/api/v1/ping")

    snap = metrics.snapshot()
    assert snap["request_count"] == before + 2
    assert snap["avg_latency_ms"] >= 0
    assert snap["max_latency_ms"] >= 0
    assert snap["by_status"].get("200", 0) >= 2
    assert any(v > 0 for v in snap["latency_buckets_ms"].values())
    assert "GET /health" in snap["by_method_path"]


def test_module_logger_convention() -> None:
    logger = get_logger(__name__)
    assert logger.name == __name__


def test_contextvar_cleared_after_request(client: TestClient) -> None:
    client.get("/health", headers={"X-Request-ID": "should-clear"})
    assert get_request_id() is None


def test_no_print_in_application_modules() -> None:
    """Architecture rule: never use print() in app code."""
    import re
    from pathlib import Path

    print_call = re.compile(r"\bprint\s*\(")
    app_root = Path(__file__).resolve().parents[1] / "app"
    offenders: list[str] = []
    for path in app_root.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        for i, line in enumerate(text.splitlines(), start=1):
            stripped = line.lstrip()
            if stripped.startswith("#"):
                continue
            if print_call.search(line):
                offenders.append(f"{path.relative_to(app_root)}:{i}")
    assert offenders == [], f"print() found in app code: {offenders}"

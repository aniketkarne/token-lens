"""Tests for /api/budget/check server endpoint."""
from __future__ import annotations

import json
import socket
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path
from types import SimpleNamespace

import pytest

from token_lens.server import _ReportStore, build_server

# Local alias so the Flask-style ``json=`` parameter below doesn't shadow
# the module inside the test client.
json_dumps = json.dumps
json_loads = json.loads


# --- Lightweight test client -------------------------------------------------
#
# The repo's existing test_server.py drives the server over a real socket via
# ``urllib``. For the budget endpoint we want a Flask-like ``client.post(path,
# json=...)`` helper, so we build a tiny wrapper around the same primitives
# (ThreadingHTTPServer + urllib) and expose it as a ``client`` fixture.


def _free_port() -> int:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


class _ServerThread:
    def __init__(self, host: str, port: int, cache: Path):
        self.store = _ReportStore(cache)
        self.httpd = build_server(host, port, self.store)
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)

    def start(self) -> None:
        self.thread.start()

    def stop(self) -> None:
        self.httpd.shutdown()
        self.httpd.server_close()
        self.thread.join(timeout=5)


class _Client:
    """Flask-lite: ``client.post(path, json={...})`` -> ``resp.status_code``."""

    def __init__(self, base: str):
        self.base = base

    def post(self, path: str, json=None, data: bytes | None = None):  # noqa: A002
        body: bytes | None = data
        if json is not None:
            body = json_dumps(json).encode("utf-8")
        req = urllib.request.Request(self.base + path, method="POST", data=body)
        if body is not None:
            req.add_header("content-type", "application/json")
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                raw = r.read()
                return self._make_response(r.status, raw, dict(r.headers))
        except urllib.error.HTTPError as e:
            raw = e.read()
            return self._make_response(e.code, raw, dict(e.headers) if e.headers else {})

    def get_json(self):
        return self._parsed

    def _make_response(self, status, raw, headers):
        parsed = None
        ct = headers.get("content-type", "") if headers else ""
        if "json" in ct:
            try:
                parsed = json_loads(raw)
            except Exception:
                parsed = None
        return _Response(status_code=status, raw=raw, headers=headers, _parsed=parsed)


class _Response(SimpleNamespace):
    def get_json(self):
        return self._parsed


@pytest.fixture
def client(tmp_path: Path):
    host, port = "127.0.0.1", _free_port()
    srv = _ServerThread(host, port, tmp_path / "cache")
    srv.start()
    base = f"http://{host}:{port}"
    deadline = time.time() + 2.0
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(base + "/healthz", timeout=0.5) as r:
                if r.status == 200:
                    break
        except Exception:
            time.sleep(0.02)
    yield _Client(base)
    srv.stop()


# --- The actual tests --------------------------------------------------------


def test_budget_check_endpoint_with_breach(client):
    resp = client.post("/api/budget/check", json={
        "config": {"budgets": {"total_tokens": 100}},
        "trace": {"model": "gpt-4o", "messages": [
            {"role": "system", "content": "x" * 1000},
            {"role": "user", "content": "hi"},
        ]},
    })
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["ok"] is False
    assert any(b["code"] == "total_tokens" for b in body["breaches"])


def test_budget_check_endpoint_under_budget(client):
    resp = client.post("/api/budget/check", json={
        "config": {"budgets": {"total_tokens": 100000}},
        "trace": {"model": "gpt-4o", "messages": [
            {"role": "system", "content": "hi"},
            {"role": "user", "content": "hello"},
        ]},
    })
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["ok"] is True
    assert body["breaches"] == []


def test_budget_check_endpoint_returns_trace_summary(client):
    resp = client.post("/api/budget/check", json={
        "config": {"budgets": {"total_tokens": 100000}},
        "trace": {"model": "gpt-4o", "messages": [
            {"role": "system", "content": "hi"},
            {"role": "user", "content": "hello"},
        ]},
    })
    body = resp.get_json()
    assert "trace_summary" in body
    assert body["trace_summary"]["model"] == "gpt-4o"


def test_budget_check_endpoint_bad_request(client):
    resp = client.post("/api/budget/check", json={"config": {}})
    assert resp.status_code in (400, 422)
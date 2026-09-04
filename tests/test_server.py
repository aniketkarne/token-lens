"""Tests for the stdlib web server in :mod:`token_lens.server`."""

from __future__ import annotations

import json
import socket
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

import pytest

from token_lens import server as server_mod
from token_lens.server import _ReportStore, build_server


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


@pytest.fixture
def running_server(tmp_path: Path):
    host, port = "127.0.0.1", _free_port()
    srv = _ServerThread(host, port, tmp_path / "cache")
    srv.start()
    base = f"http://{host}:{port}"
    # wait for socket
    deadline = time.time() + 2.0
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(base + "/healthz", timeout=0.5) as r:
                if r.status == 200:
                    break
        except Exception:
            time.sleep(0.02)
    yield base, srv.store
    srv.stop()


def _http(base: str, path: str, *, method: str = "GET", body: bytes | None = None,
          content_type: str | None = None) -> tuple[int, dict, bytes]:
    req = urllib.request.Request(base + path, method=method)
    if body is not None:
        req.data = body
    if content_type:
        req.add_header("content-type", content_type)
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            data = r.read()
            return r.status, dict(r.headers), data
    except urllib.error.HTTPError as e:
        data = e.read()
        return e.code, dict(e.headers), data


def test_healthz(running_server):
    base, _ = running_server
    status, headers, body = _http(base, "/healthz")
    assert status == 200
    assert b"ok" in body


def test_index_html(running_server):
    base, _ = running_server
    status, headers, body = _http(base, "/")
    assert status == 200
    assert b"text/html" in headers.get("content-type", "").encode()
    assert b"token-lens" in body
    # hero svg ships inline
    assert b"<svg" in body
    # hero labels its three zones (token-lens-specific, not generic)
    assert b"rag" in body
    assert b"system" in body
    assert b"user" in body


def test_hero_asset_route(running_server):
    """The hero SVG is served as a standalone asset."""
    base, _ = running_server
    status, headers, body = _http(base, "/assets/hero.svg")
    assert status == 200
    assert "image/svg+xml" in headers.get("content-type", "")
    assert body.lstrip().startswith(b"<svg")


def test_hero_asset_ships_in_repo():
    """assets/hero.svg must exist in the checkout (not just inline art)."""
    p = server_mod._hero_asset_path()
    assert p is not None, "assets/hero.svg missing from the distribution"
    text = p.read_text(encoding="utf-8")
    assert text.lstrip().startswith("<svg")
    for zone in ("rag", "system", "user"):
        assert zone in text


def test_api_sample(running_server):
    base, _ = running_server
    status, _, body = _http(base, "/api/sample")
    assert status == 200
    payload = json.loads(body)
    assert "messages" in payload
    assert "model" in payload


def test_upload_and_download(running_server, sample_trace):
    base, _ = running_server
    body = json.dumps(sample_trace).encode("utf-8")
    status, _, resp = _http(base, "/api/upload", method="POST",
                            body=body, content_type="application/json")
    assert status == 200, resp
    payload = json.loads(resp)
    rid = payload["report_id"]
    assert rid

    # report id is reachable
    status, _, body = _http(base, f"/api/report/{rid}")
    assert status == 200
    summary = json.loads(body)
    assert summary["total_tokens"] > 0

    # downloads
    for fmt in ("html", "svg", "json", "trace"):
        status, headers, body = _http(base, f"/api/download/{rid}/{fmt}")
        assert status == 200, (fmt, body[:200])
        if fmt == "html":
            assert b"token-lens report" in body
        elif fmt == "svg":
            assert body.startswith(b"<svg")
        elif fmt == "json":
            json.loads(body)
        elif fmt == "trace":
            json.loads(body)

    # inline report route
    status, headers, body = _http(base, f"/reports/{rid}")
    assert status == 200
    assert b"token-lens report" in body


def test_upload_bad_json(running_server):
    base, _ = running_server
    status, _, body = _http(base, "/api/upload", method="POST",
                            body=b"not-json", content_type="application/json")
    assert status == 400
    assert b"invalid JSON" in body


def test_upload_multipart(running_server, sample_trace):
    base, _ = running_server
    boundary = "----tlbound"
    body_json = json.dumps(sample_trace).encode("utf-8")
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="trace.json"\r\n'
        f"Content-Type: application/json\r\n\r\n"
    ).encode() + body_json + f"\r\n--{boundary}--\r\n".encode()
    status, _, resp = _http(
        base, "/api/upload", method="POST", body=body,
        content_type=f"multipart/form-data; boundary={boundary}",
    )
    assert status == 200, resp
    payload = json.loads(resp)
    assert payload["report_id"]


def test_unknown_report_id(running_server):
    base, _ = running_server
    status, _, body = _http(base, "/api/report/nope-not-a-real-id")
    assert status == 404


def test_unknown_download_format(running_server):
    base, _ = running_server
    # The route only validates format for a valid regex match.
    # "totallybogus" matches the [a-z]+ format slot, so we get 400.
    status, _, body = _http(base, "/api/download/aaaa1234/totallybogus")
    assert status == 400
    # And a route with an unsupported format returns 400 either way
    # (the regex is permissive but the handler still rejects it).
    # An unparseable segment falls through to 404, which is correct.


def test_unknown_route(running_server):
    base, _ = running_server
    status, _, body = _http(base, "/totally/not/a/route")
    assert status == 404


def test_main_serve_once(tmp_path: Path, sample_trace, capsys):
    """``token-lens serve --once`` should handle one request and exit."""
    import urllib.request as ur

    port = _free_port()
    host = "127.0.0.1"
    cache = tmp_path / "cache"

    # Start the server in a thread that handles one request, then exits.
    from token_lens.server import main as serve_main
    import threading

    box = {}

    def _run():
        rc = serve_main([
            "--host", host, "--port", str(port),
            "--cache", str(cache), "--once",
        ])
        box["rc"] = rc

    t = threading.Thread(target=_run, daemon=True)
    t.start()
    # Give the server a moment to bind
    time.sleep(0.1)
    body = json.dumps(sample_trace).encode("utf-8")
    req = ur.Request(
        f"http://{host}:{port}/api/upload",
        method="POST",
        data=body,
        headers={"content-type": "application/json"},
    )
    with ur.urlopen(req, timeout=5) as r:
        assert r.status == 200
        payload = json.loads(r.read())
        assert payload["report_id"]
    t.join(timeout=5)
    assert box.get("rc") == 0

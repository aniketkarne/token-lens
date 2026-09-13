"""Tail a JSONL log file and ingest new lines into the TraceStore."""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

from ..store import TraceStore
from .normalize import normalize


def _read_offset(offset_path):
    if not offset_path.exists():
        return 0
    try:
        return int(offset_path.read_text().strip())
    except (ValueError, OSError):
        return 0


def _write_offset_atomic(offset_path, offset):
    tmp = offset_path.with_suffix(offset_path.suffix + ".tmp")
    tmp.write_text(str(int(offset)), encoding="utf-8")
    os.replace(tmp, offset_path)


def tail_jsonl(path, store, source="generic", follow=False, offset_path=None):
    p = Path(path)
    if not p.exists():
        return 0

    op = Path(offset_path) if offset_path else p.with_suffix(p.suffix + ".offset")
    start_offset = _read_offset(op)

    inserted = 0

    def _ingest_pass():
        nonlocal inserted
        count = 0
        with p.open("r", encoding="utf-8") as fh:
            fh.seek(start_offset)
            current_offset = start_offset
            for raw in fh:
                line = raw.rstrip("\n")
                current_offset += len(raw.encode("utf-8"))
                if not line.strip():
                    continue
                try:
                    payload = json.loads(line)
                except json.JSONDecodeError:
                    print("warning: skipping invalid JSON line in " + str(p), file=sys.stderr)
                    continue
                trace = normalize(payload, source=source)
                store.insert_trace(trace)
                count += 1
            _write_offset_atomic(op, current_offset)
        inserted += count
        return count

    _ingest_pass()

    if follow:
        try:
            while True:
                time.sleep(1.0)
                start_offset = _read_offset(op)
                _ingest_pass()
        except KeyboardInterrupt:
            pass

    return inserted


__all__ = ["tail_jsonl"]

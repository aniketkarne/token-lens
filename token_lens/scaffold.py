"""Scaffold a token-lens config into the current directory."""
from __future__ import annotations

import importlib.resources as resources
from pathlib import Path


class FileExists(Exception):
    """Raised when scaffold() would overwrite an existing file and force=False."""


_TEMPLATE_FILES: tuple[tuple[str, str], ...] = (
    ("token-lens.yaml", "token-lens.yaml"),
    ("github-actions.yml", ".github/workflows/token-lens.yml"),
    ("sample_trace.json", "examples/sample_trace.json"),
    ("README_TOKENLENS.md", "README_TOKENLENS.md"),
)


def _read_template(name: str) -> str:
    return resources.files("token_lens").joinpath(f"templates/{name}").read_text(encoding="utf-8")


def scaffold(target_dir, force: bool = False) -> list:
    target = Path(target_dir).resolve()
    written = []
    if not force:
        existing = [target / rel for _, rel in _TEMPLATE_FILES if (target / rel).exists()]
        if existing:
            paths = ", ".join(str(p.relative_to(target)) for p in existing)
            raise FileExists(
                f"refusing to overwrite existing file(s): {paths}. Use --force to overwrite."
            )
    for tmpl_name, rel in _TEMPLATE_FILES:
        dest = target / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(_read_template(tmpl_name), encoding="utf-8")
        written.append(dest)
    return written


__all__ = ["scaffold", "FileExists"]
"""Pin the resources and imports that must survive a wheel install.

These run from a source checkout (where everything is present by accident);
the CI wheel-smoke job re-verifies the same surface from an installed wheel.
If you add a runtime resource, add it here AND to
[tool.setuptools.package-data] in pyproject.toml.
"""
from __future__ import annotations

import importlib
import importlib.resources as resources
import re

import token_lens


def _resource(*parts):
    return resources.files("token_lens").joinpath(*parts)


def test_templates_shipped():
    for name in ("token-lens.yaml", "github-actions.yml", "sample_trace.json", "README_TOKENLENS.md"):
        assert _resource("templates", name).is_file(), name


def test_demo_traces_shipped():
    for name in ("bloated_trace.json", "lean_trace.json"):
        assert _resource("data", name).is_file(), name


def test_ingest_subpackage_importable():
    importlib.import_module("token_lens.ingest.jsonl")
    importlib.import_module("token_lens.ingest.normalize")


def test_readme_python_api_import_works():
    # exact import line from the README Python API section
    from token_lens import analyze_file, score_chunk_usefulness  # noqa: F401


def test_version_matches_pyproject(repo_root):
    pyproject = (repo_root / "pyproject.toml").read_text(encoding="utf-8")
    m = re.search(r'^version = "([^"]+)"', pyproject, re.MULTILINE)
    assert m, "pyproject.toml must declare a version"
    assert token_lens.__version__ == m.group(1)


def test_scaffold_writes_all_templates(tmp_path):
    from token_lens.scaffold import scaffold

    written = scaffold(tmp_path)
    rels = {str(p.relative_to(tmp_path)) for p in written}
    assert rels == {
        "token-lens.yaml",
        ".github/workflows/token-lens.yml",
        "examples/sample_trace.json",
        "README_TOKENLENS.md",
    }

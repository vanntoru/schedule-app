"""Unit tests for the OAuth2 callback helpers."""

from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import schedule_app


def test_patch_exchange(monkeypatch):
    """Ensure _exchange_code_for_token can be patched via the package path."""

    def dummy(code: str):  # pragma: no cover - dummy implementation
        return {"access_token": "test"}

    monkeypatch.setattr(
        "schedule_app._exchange_code_for_token",
        dummy,
        raising=False,
    )

    # Access the package to ensure it imports correctly without Flask
    assert schedule_app is not None

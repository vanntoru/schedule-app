# tests/conftest.py  ★新規
"""Pytest configuration.

Tests rely on ``freezegun`` for time manipulation. They are skipped if the
package isn't installed.
"""
import sys
import pathlib
import importlib
import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

if importlib.util.find_spec("freezegun") is None:
    pytest.skip("freezegun is required to run tests", allow_module_level=True)

"""Smoke tests for Milestone 1.1 project bootstrap."""

from app import __version__
from app.main import app


def test_package_version() -> None:
    assert __version__ == "0.1.0"


def test_fastapi_app_imports() -> None:
    assert app.title == "Industrial Brain AI"
    assert app.version == "0.1.0"

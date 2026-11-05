import os
import pytest


@pytest.fixture(autouse=True)
def setup_test_auth(monkeypatch):
    """
    Ensures existing unit tests that don't transmit tokens can test application
    logic without failing on auth.
    """
    monkeypatch.setenv("ENABLE_TEST_DEMO_FALLBACK", "1")
    yield

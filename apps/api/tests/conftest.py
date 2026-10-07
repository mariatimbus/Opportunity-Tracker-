"""Test fixtures: TestClient with test settings (sqlite in-memory)."""

import os

os.environ["DATABASE_URL"] = "sqlite://"  # in-memory, per-connection

import pytest
from fastapi.testclient import TestClient

from opportunity_api.main import create_app


@pytest.fixture()
def client() -> TestClient:
    return TestClient(create_app())

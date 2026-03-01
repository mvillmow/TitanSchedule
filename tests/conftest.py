import json
from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def load_fixture(name: str) -> dict | list:
    """Load a JSON fixture file by name."""
    path = FIXTURES_DIR / name
    with open(path) as f:
        return json.load(f)


@pytest.fixture
def fixtures_dir() -> Path:
    return FIXTURES_DIR

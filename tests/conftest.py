import json
from collections.abc import Callable, Iterator
from pathlib import Path

import pytest

from example_app.settings import get_settings

GOLDEN_DIR = Path(__file__).parent / "golden"


def pytest_addoption(parser):
    parser.addoption("--update-golden", action="store_true", help="rewrite golden files")


@pytest.fixture
def fresh_settings() -> Iterator[None]:
    """Drop the get_settings() singleton around a test so it never leaks."""
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def golden(request) -> Callable[[str, object], None]:
    update = request.config.getoption("--update-golden")

    def check(name: str, data: object) -> None:
        path = GOLDEN_DIR / f"{name}.json"
        actual = json.dumps(data, indent=2, sort_keys=True, default=str) + "\n"
        if update or not path.exists():
            path.write_text(actual)
            if not update:
                pytest.fail(f"golden {path.name} did not exist; created it — review and re-run")
            return
        assert actual == path.read_text(), f"golden mismatch: {path} (use --update-golden)"

    return check

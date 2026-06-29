"""E2E test configuration.

This conftest.py handles pytest CLI options and shared fixtures
for the E2E test suite.
"""

import pytest


def pytest_addoption(parser: pytest.Parser) -> None:
    """Add command line options for E2E tests."""
    parser.addoption(
        "--e2e-live",
        action="store_true",
        default=False,
        help="Run live E2E tests against running services",
    )


@pytest.fixture
def live_mode(request: pytest.FixtureRequest) -> bool:
    """Return True if running in live E2E mode."""
    return request.config.getoption("--e2e-live", False)

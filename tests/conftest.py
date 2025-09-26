"""
Global fixtures for the pytest test suite.
"""

from unittest.mock import AsyncMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.fixture
def mock_session() -> AsyncMock:
    """
    Creates a mock of the SQLAlchemy AsyncSession using AsyncMock.
    This allows us to `await` methods like `commit` and `rollback`
    and use `assert_awaited_once` for verification.
    """
    return AsyncMock(spec=AsyncSession)

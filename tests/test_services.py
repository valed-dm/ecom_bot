"""
Unit tests for the service layer.

These tests focus on the business logic within the service functions,
and they "mock" the database (CRUD) layer to ensure the service can be
tested in isolation.
"""

import pytest
from pytest_mock import MockerFixture
from sqlalchemy.ext.asyncio import AsyncSession

from ecombot.schemas.dto import CategoryDTO
from ecombot.services import catalog_service


pytestmark = pytest.mark.asyncio


async def test_get_all_categories_returns_correct_dtos(
    mocker: MockerFixture, mock_session: AsyncSession
):
    """
    Tests that the get_all_categories service correctly calls the CRUD layer
    and converts the database models into a list of CategoryDTOs.
    """

    class MockCategory:
        def __init__(self, id, name, description):
            self.id = id
            self.name = name
            self.description = description

    fake_db_categories = [
        MockCategory(id=1, name="Laptops", description="Powerful notebooks"),
        MockCategory(id=2, name="Mobiles", description="Smartphones"),
    ]
    mock_crud_get_categories = mocker.patch(
        "ecombot.services.catalog_service.crud.get_categories",
        return_value=fake_db_categories,
    )
    result_dtos = await catalog_service.get_all_categories(mock_session)
    mock_crud_get_categories.assert_called_once_with(mock_session)

    assert len(result_dtos) == 2
    assert all(isinstance(dto, CategoryDTO) for dto in result_dtos)
    assert result_dtos[0].id == 1
    assert result_dtos[0].name == "Laptops"
    assert result_dtos[1].id == 2
    assert result_dtos[1].name == "Mobiles"

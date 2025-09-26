from unittest.mock import AsyncMock
from unittest.mock import MagicMock

import pytest
from pytest_mock import MockerFixture

from ecombot.db.models import Cart
from ecombot.services import cart_service
from ecombot.services.cart_service import InsufficientStockError


async def test_add_product_to_cart_success(
    mocker: MockerFixture, mock_session: AsyncMock
):
    """
    Tests the successful addition of a product to the cart.
    Verifies that the correct CRUD functions are called and a commit happens.
    """
    user_id = 123
    product_id = 1

    mock_product = MagicMock()
    mock_product.id = product_id
    mock_product.stock = 10

    mock_cart = MagicMock()

    mock_get_product = mocker.patch(
        "ecombot.services.cart_service.crud.get_product", return_value=mock_product
    )
    mock_get_cart_lean = mocker.patch(
        "ecombot.services.cart_service.crud.get_or_create_cart_lean",
        return_value=mock_cart,
    )
    mock_add_item = mocker.patch("ecombot.services.cart_service.crud.add_item_to_cart")

    # Mock the final eager-loading call to return a DTO-ready object
    mock_get_cart_full = mocker.patch(
        "ecombot.services.cart_service.crud.get_or_create_cart",
        return_value=MagicMock(spec=Cart),
    )
    # Mock the Pydantic validator
    mock_model_validate = mocker.patch("ecombot.schemas.dto.CartDTO.model_validate")

    await cart_service.add_product_to_cart(
        session=mock_session, user_id=user_id, product_id=product_id, quantity=1
    )

    mock_get_product.assert_called_once_with(mock_session, product_id)
    mock_get_cart_lean.assert_called_once_with(mock_session, user_id)
    mock_add_item.assert_called_once_with(
        session=mock_session, cart=mock_cart, product=mock_product, quantity=1
    )
    # Verify that the transaction was committed
    mock_session.commit.assert_awaited_once()

    # Verify the final re-fetch and DTO conversion happened
    mock_get_cart_full.assert_called_once_with(mock_session, user_id)
    mock_model_validate.assert_called_once()


async def test_add_product_to_cart_insufficient_stock_raises_error(
    mocker: MockerFixture, mock_session: AsyncMock
):
    """
    Tests that the service correctly raises an InsufficientStockError
    if the product's stock is too low.
    """
    user_id = 123
    product_id = 1

    mock_product = MagicMock()
    mock_product.stock = 0

    mocker.patch(
        "ecombot.services.cart_service.crud.get_product", return_value=mock_product
    )

    with pytest.raises(InsufficientStockError):
        await cart_service.add_product_to_cart(
            session=mock_session, user_id=user_id, product_id=product_id, quantity=1
        )

    # A commit was NEVER called, because the transaction should fail.
    mock_session.commit.assert_not_awaited()

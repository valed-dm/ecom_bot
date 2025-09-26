from unittest.mock import AsyncMock
from unittest.mock import MagicMock

import pytest
from pytest_mock import MockerFixture

from ecombot.db.models import Cart
from ecombot.db.models import CartItem
from ecombot.db.models import DeliveryAddress
from ecombot.db.models import Order
from ecombot.db.models import User
from ecombot.services import order_service
from ecombot.services import user_service
from ecombot.services.order_service import OrderPlacementError
from ecombot.services.user_service import AddressNotFoundError


async def test_update_profile_details(mocker: MockerFixture, mock_session: AsyncMock):
    """
    Tests that the user profile update service calls the correct CRUD function.
    """
    user_id = 1
    update_data = {"phone": "555-5555"}
    mock_user = MagicMock(spec=User)

    mock_update_crud = mocker.patch(
        "ecombot.services.user_service.crud.update_user_profile", return_value=mock_user
    )
    mocker.patch("ecombot.schemas.dto.UserProfileDTO.model_validate")

    await user_service.update_profile_details(
        session=mock_session, user_id=user_id, update_data=update_data
    )

    mock_update_crud.assert_called_once_with(mock_session, user_id, update_data)
    mock_session.commit.assert_awaited_once()


async def test_place_order_success(mocker: MockerFixture, mock_session: AsyncMock):
    """
    Tests the successful placement of an order from a cart.
    """
    mock_user = MagicMock(
        spec=User,
        id=1,
        telegram_id=123,
        phone="555-1234",
        first_name="Test User",
    )
    mock_address = MagicMock(spec=DeliveryAddress, id=1, full_address="123 Main St")
    mock_cart_item = MagicMock(spec=CartItem, product_id=10, quantity=2)
    mock_cart = MagicMock(spec=Cart, items=[mock_cart_item])
    mock_order = MagicMock(spec=Order, id=99, order_number="ECO-TEST-123")

    mock_get_cart = mocker.patch(
        "ecombot.services.order_service.crud.get_or_create_cart",
        return_value=mock_cart,
    )
    mock_create_order = mocker.patch(
        "ecombot.services.order_service.crud.create_order_with_items",
        return_value=mock_order,
    )
    mock_clear_cart = mocker.patch("ecombot.services.order_service.crud.clear_cart")
    mock_get_order = mocker.patch(
        "ecombot.services.order_service.crud.get_order",
        return_value=mock_order,
    )
    mock_validate = mocker.patch("ecombot.schemas.dto.OrderDTO.model_validate")

    await order_service.place_order(
        session=mock_session, db_user=mock_user, delivery_address=mock_address
    )

    mock_get_cart.assert_called_once_with(mock_session, mock_user.telegram_id)
    mock_create_order.assert_called_once()
    mock_clear_cart.assert_called_once_with(mock_session, mock_cart)
    mock_session.commit.assert_awaited_once()
    mock_get_order.assert_called_once_with(mock_session, 99)
    mock_validate.assert_called_once_with(mock_order)


async def test_place_order_insufficient_stock_raises_error(
    mocker: MockerFixture, mock_session: AsyncMock
):
    """
    Tests that place_order raises an error and rolls back if stock is insufficient.
    """
    mock_user = MagicMock(spec=User, id=1, telegram_id=123)
    mock_address = MagicMock(spec=DeliveryAddress, id=1)
    mock_cart = MagicMock(spec=Cart, items=[MagicMock(spec=CartItem)])

    mocker.patch(
        "ecombot.services.order_service.crud.get_or_create_cart", return_value=mock_cart
    )
    mocker.patch(
        "ecombot.services.order_service.crud.create_order_with_items",
        side_effect=ValueError("Not enough stock!"),
    )

    with pytest.raises(OrderPlacementError, match="Not enough stock!"):
        await order_service.place_order(
            session=mock_session, db_user=mock_user, delivery_address=mock_address
        )

    mock_session.rollback.assert_awaited_once()
    mock_session.commit.assert_not_awaited()


async def test_delete_address_success(mocker: MockerFixture, mock_session: AsyncMock):
    """
    Tests the successful deletion of a delivery address.
    Verifies that the CRUD function is called and the transaction is committed.
    """
    user_id = 1
    address_id = 101

    mock_delete_crud = mocker.patch(
        "ecombot.services.user_service.crud.delete_delivery_address",
        return_value=True,
    )

    await user_service.delete_address(
        session=mock_session, user_id=user_id, address_id=address_id
    )

    # 1. Verify that the correct CRUD function was called with the right arguments.
    mock_delete_crud.assert_called_once_with(mock_session, address_id, user_id)

    # 2. Verify that the transaction was successfully committed.
    mock_session.commit.assert_awaited_once()

    # 3. Verify that a rollback was NOT called.
    mock_session.rollback.assert_not_awaited()


async def test_delete_address_not_found_raises_error(
    mocker: MockerFixture, mock_session: AsyncMock
):
    """
    Tests that an AddressNotFoundError is raised if the CRUD layer reports
    that the address was not found or did not belong to the user.
    Also verifies that the transaction is rolled back.
    """
    user_id = 1
    address_id = 101

    mocker.patch(
        "ecombot.services.user_service.crud.delete_delivery_address",
        return_value=False,  # Simulate that the address was not found
    )

    with pytest.raises(
        AddressNotFoundError, match="Address not found or permission denied."
    ):
        await user_service.delete_address(
            session=mock_session, user_id=user_id, address_id=address_id
        )

    # Verify that the transaction was ROLLED BACK.
    mock_session.rollback.assert_awaited_once()

    # Verify that the transaction was NEVER COMMITTED.
    mock_session.commit.assert_not_awaited()

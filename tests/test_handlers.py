"""
Integration tests for the bot handlers.

These tests directly call the handler functions and use pytest-mock to
simulate aiogram objects and service layer responses. This provides a
stable and library-independent way to test handler logic.
"""

from decimal import Decimal
from unittest.mock import AsyncMock
from unittest.mock import MagicMock

from pytest_mock import MockerFixture

from ecombot.bot.callback_data import CartCallbackFactory
from ecombot.bot.callback_data import CatalogCallbackFactory
from ecombot.bot.handlers.cart import add_to_cart_handler
from ecombot.bot.handlers.cart import view_cart_handler
from ecombot.bot.handlers.catalog import command_start_handler
from ecombot.bot.handlers.catalog import view_category_handler
from ecombot.bot.handlers.profile import profile_handler
from ecombot.db.models import User
from ecombot.schemas.dto import CartDTO
from ecombot.schemas.dto import CartItemDTO
from ecombot.schemas.dto import CategoryDTO
from ecombot.schemas.dto import DeliveryAddressDTO
from ecombot.schemas.dto import ProductDTO
from ecombot.schemas.dto import UserProfileDTO
from ecombot.services.cart_service import InsufficientStockError


async def test_start_command_handler(mocker: MockerFixture):
    """
    Tests the /start command handler.
    Verifies that it calls the correct service and sends a reply
     with the correct text and keyboard.
    """
    fake_categories = [
        CategoryDTO(id=1, name="Laptops", description="..."),
        CategoryDTO(id=2, name="Mobiles", description="..."),
    ]
    mocker.patch(
        "ecombot.bot.handlers.catalog.catalog_service.get_all_categories",
        return_value=fake_categories,
    )

    mock_message = AsyncMock()
    mock_session = AsyncMock()

    await command_start_handler(message=mock_message, session=mock_session)

    mock_message.answer.assert_awaited_once()

    call_args = mock_message.answer.call_args

    reply_text = call_args.args[0]
    assert "Welcome to our store!" in reply_text

    reply_markup = call_args.kwargs["reply_markup"]
    assert reply_markup is not None
    assert len(reply_markup.inline_keyboard) == 1
    assert len(reply_markup.inline_keyboard[0]) == 2
    assert reply_markup.inline_keyboard[0][0].text == "Laptops"


async def test_view_category_handler(mocker: MockerFixture):
    """
    Tests the handler for viewing products within a category.
    """
    mock_category = CategoryDTO(id=1, name="Laptops", description="...")
    fake_products = [
        ProductDTO(
            id=10,
            name="iPhone 17",
            description="...",
            price=Decimal("999.99"),
            category=mock_category,
        ),
    ]
    mock_get_products = mocker.patch(
        "ecombot.bot.handlers.catalog.catalog_service.get_products_in_category",
        return_value=fake_products,
    )

    callback_data = CatalogCallbackFactory(action="view_category", item_id=1)
    mock_message = AsyncMock()
    mock_message.photo = None

    mock_query = AsyncMock(data=callback_data.pack())
    mock_query.message = mock_message

    mock_bot = AsyncMock()
    mock_session = AsyncMock()

    await view_category_handler(
        query=mock_query,
        callback_data=callback_data,
        session=mock_session,
        callback_message=mock_message,
        bot=mock_bot,
    )

    # Verify the service was called correctly.
    mock_get_products.assert_called_once_with(mock_session, 1)

    # Verify the original message was edited.
    mock_message.edit_text.assert_awaited_once()

    # Get the positional and keyword arguments from the call.
    call_args = mock_message.edit_text.call_args

    # The reply text is the FIRST positional argument.
    reply_text = call_args.args[0]
    assert "Here are the products" in reply_text

    # The keyboard is a keyword argument.
    reply_markup = call_args.kwargs["reply_markup"]
    assert "iPhone 17" in str(reply_markup)
    assert "Back to Categories" in str(reply_markup)

    # Verify the callback query was answered.
    mock_query.answer.assert_awaited_once()


async def test_view_cart_handler_with_items(mocker: MockerFixture):
    """
    Tests the /cart handler when the user has items in their cart.
    Verifies the correct message content and keyboard are sent.
    """
    mock_category = CategoryDTO(id=1, name="Electronics", description="")
    mock_product1 = ProductDTO(
        id=17,
        name="iPhone 17",
        description="",
        price=Decimal("1399.99"),
        category=mock_category,
    )
    mock_product2 = ProductDTO(
        id=18,
        name="Galaxy S25",
        description="",
        price=Decimal("899.97"),
        category=mock_category,
    )

    fake_cart_dto = CartDTO(
        id=1,
        user_id=12345,
        items=[
            CartItemDTO(id=101, quantity=1, product=mock_product1),
            CartItemDTO(id=102, quantity=3, product=mock_product2),
        ],
    )

    mock_get_cart = mocker.patch(
        "ecombot.bot.handlers.cart.cart_service.get_user_cart",
        return_value=fake_cart_dto,
    )

    mock_message = AsyncMock()
    mock_message.from_user.id = 12345
    mock_session = AsyncMock()

    await view_cart_handler(message=mock_message, session=mock_session)

    mock_get_cart.assert_called_once_with(mock_session, 12345)

    # Verify that the `answer` method was called.
    mock_message.answer.assert_awaited_once()

    call_args = mock_message.answer.call_args
    reply_text = call_args.args[0]
    reply_markup = call_args.kwargs["reply_markup"]

    assert "Your Shopping Cart" in reply_text
    assert "iPhone 17" in reply_text
    assert "Galaxy S25" in reply_text
    assert "$4,099.90" in reply_text  # (1 * 1399.99) + (3 * 899.97) = 4,099.90
    assert "Checkout" in str(reply_markup)
    assert "Catalog" in str(reply_markup)


async def test_view_cart_handler_empty_cart(mocker: MockerFixture):
    """
    Tests the /cart handler when the user's cart is empty.
    """

    fake_empty_cart_dto = CartDTO(id=1, user_id=12345, items=[])

    mocker.patch(
        "ecombot.bot.handlers.cart.cart_service.get_user_cart",
        return_value=fake_empty_cart_dto,
    )

    mock_message = AsyncMock()
    mock_message.from_user.id = 12345
    mock_session = AsyncMock()

    await view_cart_handler(message=mock_message, session=mock_session)

    mock_message.answer.assert_awaited_once()

    call_args = mock_message.answer.call_args
    reply_text = call_args.args[0]
    reply_markup = call_args.kwargs["reply_markup"]

    assert "Your cart is currently empty" in reply_text
    assert "Checkout" not in str(reply_markup)
    assert "Catalog" in str(reply_markup)


async def test_profile_handler_displays_correct_info(mocker: MockerFixture):
    """
    Tests the /profile command handler.
    Verifies that it correctly fetches the user profile and displays
    the information along with the management keyboard.
    """
    fake_profile_dto = UserProfileDTO(
        telegram_id=12345,
        first_name="Test User",
        phone="+15551234567",
        email="test@example.com",
        addresses=[
            DeliveryAddressDTO(
                id=1, address_label="Home", full_address="123 Main St", is_default=True
            )
        ],
    )

    mock_get_profile = mocker.patch(
        "ecombot.bot.handlers.profile.user_service.get_user_profile",
        return_value=fake_profile_dto,
    )

    mock_message = AsyncMock()
    mock_session = AsyncMock()
    mock_db_user = MagicMock(spec=User)

    await profile_handler(
        message=mock_message, session=mock_session, db_user=mock_db_user
    )

    mock_get_profile.assert_called_once_with(mock_session, mock_db_user)
    mock_message.answer.assert_awaited_once()

    call_args = mock_message.answer.call_args
    reply_text = call_args.args[0]
    reply_markup = call_args.kwargs["reply_markup"]

    assert "Your Profile" in reply_text
    assert "Test User" in reply_text
    assert "+15551234567" in reply_text
    assert "test@example.com" in reply_text
    assert "Default Address" in reply_text
    assert "123 Main St" in reply_text

    assert "Edit Phone" in str(reply_markup)
    assert "Edit Email" in str(reply_markup)
    assert "Manage Addresses" in str(reply_markup)


async def test_add_to_cart_handler_success(mocker: MockerFixture):
    """
    Tests the "Add to Cart" callback handler for the successful case.
    Verifies the service is called and a success pop-up is shown.
    """
    mock_add_to_cart_service = mocker.patch(
        "ecombot.bot.handlers.cart.cart_service.add_product_to_cart", return_value=None
    )

    callback_data = CartCallbackFactory(action="add", item_id=17)
    mock_query = AsyncMock(data=callback_data.pack())
    mock_query.from_user.id = 12345

    mock_session = AsyncMock()

    await add_to_cart_handler(
        query=mock_query, callback_data=callback_data, session=mock_session
    )

    mock_add_to_cart_service.assert_called_once_with(
        session=mock_session, user_id=12345, product_id=17
    )

    call_args = mock_add_to_cart_service.call_args

    assert call_args.kwargs["session"] == mock_session
    assert call_args.kwargs["user_id"] == 12345
    assert call_args.kwargs["product_id"] == 17
    assert "quantity" not in call_args.kwargs

    mock_query.answer.assert_awaited_once_with(
        "✅ Product added to your cart!", show_alert=False
    )


async def test_add_to_cart_handler_insufficient_stock(mocker: MockerFixture):
    """
    Tests the "Add to Cart" handler when the service reports insufficient stock.
    Verifies the correct error pop-up is shown to the user.
    """
    mocker.patch(
        "ecombot.bot.handlers.cart.cart_service.add_product_to_cart",
        side_effect=InsufficientStockError("Sorry, this item is out of stock."),
    )

    callback_data = CartCallbackFactory(action="add", item_id=17)
    mock_query = AsyncMock(data=callback_data.pack())
    mock_query.from_user.id = 12345
    mock_session = AsyncMock()

    await add_to_cart_handler(
        query=mock_query, callback_data=callback_data, session=mock_session
    )

    mock_query.answer.assert_awaited_once_with(
        "Sorry, this item is out of stock.", show_alert=True
    )

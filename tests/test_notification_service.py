"""
Unit tests for the notification_service.
"""

from unittest.mock import AsyncMock
from unittest.mock import MagicMock

import pytest
from aiogram import Bot
from pytest_mock import MockerFixture

from ecombot.schemas.dto import OrderDTO
from ecombot.schemas.dto import UserSimpleDTO
from ecombot.schemas.enums import OrderStatus
from ecombot.services import notification_service


@pytest.mark.parametrize(
    "status, expected_keyword",
    [
        (OrderStatus.PROCESSING, "Processing"),
        (OrderStatus.SHIPPED, "Shipped"),
        (OrderStatus.COMPLETED, "Complete"),
        (OrderStatus.CANCELLED, "Cancelled"),
    ],
)
async def test_send_order_status_update_sends_correct_message(
    mocker: MockerFixture,
    status: OrderStatus,
    expected_keyword: str,
):
    """
    Tests that for a given order status, the correct notification
    message is constructed and sent.
    """
    # 1. Create a mock Bot object with AsyncMock because bot.send_message is async.
    mock_bot = AsyncMock(spec=Bot)

    # 2. Create a mock OrderDTO with the status for this test run.
    #    It needs a nested mock UserSimpleDTO.
    mock_user_dto = MagicMock(spec=UserSimpleDTO, telegram_id=12345)
    mock_order_dto = MagicMock(
        spec=OrderDTO, order_number="ECO-TEST-123", status=status, user=mock_user_dto
    )

    await notification_service.send_order_status_update(mock_bot, mock_order_dto)

    # 1. Verify that bot.send_message was awaited exactly once.
    mock_bot.send_message.assert_awaited_once()

    # 2. Inspect the arguments that were passed to send_message.
    #    `call_args` is a special mock attribute that captures the arguments.
    call_args, call_kwargs = mock_bot.send_message.call_args

    # Assert that the message was sent to the correct user.
    assert call_kwargs["chat_id"] == 12345

    # Assert that the generated text contains the keyword we expect for this status.
    sent_text = call_kwargs["text"]
    assert expected_keyword in sent_text


async def test_send_order_status_update_does_not_send_for_pending_status(
    mocker: MockerFixture,
):
    """
    Tests that no notification is sent for a status (like PENDING)
    that does not have a specific template.
    """
    mock_bot = AsyncMock(spec=Bot)
    mock_user_dto = MagicMock(spec=UserSimpleDTO, telegram_id=12345)
    mock_order_dto = MagicMock(
        spec=OrderDTO,
        order_number="ECO-TEST-123",
        status=OrderStatus.PENDING,  # The status we want to ignore
        user=mock_user_dto,
    )

    await notification_service.send_order_status_update(mock_bot, mock_order_dto)

    # Verify that bot.send_message was NEVER awaited.
    mock_bot.send_message.assert_not_awaited()

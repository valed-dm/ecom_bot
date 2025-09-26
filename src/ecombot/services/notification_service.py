"""
Service layer for sending notifications to users.
"""

from html import escape

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest

from ecombot.logging_setup import log
from ecombot.schemas.dto import OrderDTO
from ecombot.schemas.enums import OrderStatus


async def send_order_status_update(bot: Bot, order: OrderDTO):
    """
    Sends a notification to a user about a change in their order status.
    Uses HTML parse mode for robust formatting.
    """
    user_telegram_id = order.user.telegram_id
    text = ""
    safe_order_number = escape(order.order_number)

    status_name = order.status.name.capitalize()

    if order.status == OrderStatus.PROCESSING:
        text = (
            f"✅ **Order Status Updated: {status_name}**\n\n"
            f"Your order <code>{safe_order_number}</code> is now being processed. "
            f"We'll notify you again once it has shipped."
        )
    elif order.status == OrderStatus.SHIPPED:
        text = (
            f"🚚 **Order Status Updated: {status_name}**\n\n"
            f"Your order <code>{safe_order_number}</code> has been shipped. "
            f"You can track its progress in your /orders menu."
        )
    elif order.status == OrderStatus.COMPLETED:
        text = (
            f"🎉 **Your Order is Complete!**\n\n"
            f"Thank you for your purchase! Order: <code>{safe_order_number}</code>"
        )
    elif order.status == OrderStatus.CANCELLED:
        text = (
            f"❌ **Order Status Updated: {status_name}**\n\n"
            f"Your order <code>{safe_order_number}</code>"
            f" has been successfully cancelled."
        )

    if text:
        try:
            await bot.send_message(chat_id=user_telegram_id, text=text)
            log.info(
                f"Sent status update for order {order.order_number}"
                f" to user {user_telegram_id}"
            )
        except TelegramBadRequest as e:
            # If the user has blocked the bot
            log.warning(f"Failed to send notification to user {user_telegram_id}: {e}")
        except Exception as e:
            log.error(
                f"An unexpected error occurred sending notification to user"
                f" {user_telegram_id}: {e}",
                exc_info=True,
            )

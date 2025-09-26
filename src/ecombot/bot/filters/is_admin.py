"""
Custom filter to check if a user is an administrator.
"""

from aiogram.filters import Filter
from aiogram.types import Message

from ecombot.config import settings


class IsAdmin(Filter):
    async def __call__(self, message: Message) -> bool:
        if not message.from_user:
            return False
        return message.from_user.id in settings.ADMIN_IDS

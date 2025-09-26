"""
Service layer for user profile and address management.
"""

from typing import Any
from typing import Dict
from typing import List

from sqlalchemy.ext.asyncio import AsyncSession

from ecombot.db import crud
from ecombot.db.models import DeliveryAddress
from ecombot.db.models import User
from ecombot.schemas.dto import DeliveryAddressDTO
from ecombot.schemas.dto import UserProfileDTO


class AddressNotFoundError(Exception):
    """Raised when an address is not found or does not belong to the user."""

    pass


async def get_user_profile(session: AsyncSession, db_user: User) -> UserProfileDTO:
    """Fetches and converts a user's profile to a DTO."""
    return UserProfileDTO.model_validate(db_user)


async def update_profile_details(
    session: AsyncSession, user_id: int, update_data: Dict[str, Any]
) -> UserProfileDTO:
    """Updates a user's profile and returns the updated DTO."""
    try:
        user = await crud.update_user_profile(session, user_id, update_data)
        await session.commit()
        if not user:
            raise Exception("User not found during update.")
        return UserProfileDTO.model_validate(user)
    except Exception:
        await session.rollback()
        raise


async def get_all_user_addresses(
    session: AsyncSession, user_id: int
) -> List[DeliveryAddressDTO]:
    """Fetches all of a user's delivery addresses."""
    addresses = await crud.get_user_addresses(session, user_id)
    return [DeliveryAddressDTO.model_validate(addr) for addr in addresses]


async def add_new_address(
    session: AsyncSession, user_id: int, label: str, address: str
) -> DeliveryAddress:
    """Adds a new address for the user."""
    try:
        new_address = await crud.add_delivery_address(session, user_id, label, address)
        await session.commit()
        return new_address
    except Exception:
        await session.rollback()
        raise


async def delete_address(session: AsyncSession, user_id: int, address_id: int) -> bool:
    """Deletes a user's address after an authorization check."""
    try:
        success = await crud.delete_delivery_address(session, address_id, user_id)
        if not success:
            raise AddressNotFoundError("Address not found or permission denied.")
        await session.commit()
        return True
    except Exception:
        await session.rollback()
        raise


async def set_user_default_address(
    session: AsyncSession,
    user_id: int,
    address_id: int,
) -> bool:
    """Service-level function to set a user's default address."""
    try:
        result = await crud.set_default_address(session, user_id, address_id)
        if not result:
            raise AddressNotFoundError("Address not found or permission denied.")
        await session.commit()
        return True
    except Exception:
        await session.rollback()
        raise

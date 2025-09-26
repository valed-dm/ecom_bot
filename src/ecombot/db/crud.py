"""
CRUD (Create, Read, Update, Delete) operations for the e-commerce bot.

These functions encapsulate the database logic and are designed to be called
from within an active SQLAlchemy AsyncSession. They do not commit the session
themselves; the calling business logic (e.g., a bot handler) is responsible
for transaction management (commit/rollback).
"""

from decimal import Decimal
from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from typing import Sequence

import aiogram
from sqlalchemy import select
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..schemas.enums import OrderStatus
from ..utils import generate_order_number
from .models import Cart
from .models import CartItem
from .models import Category
from .models import DeliveryAddress
from .models import Order
from .models import OrderItem
from .models import Product
from .models import User


# -------------------
# User Functions
# -------------------


async def get_or_create_user(
    session: AsyncSession, telegram_user: "aiogram.types.User"
) -> User:
    """
    Gets a user from the DB by their Telegram ID, creating one
    if they don't exist.
    """
    stmt = (
        select(User)
        .where(User.telegram_id == telegram_user.id)
        .options(selectinload(User.addresses))
    )
    result = await session.execute(stmt)
    db_user = result.scalars().first()

    if not db_user:
        db_user = User(
            telegram_id=telegram_user.id,
            username=telegram_user.username,
            first_name=telegram_user.full_name,
        )
        session.add(db_user)
        await session.commit()
        await session.refresh(db_user, attribute_names=["addresses"])

    return db_user


# --- User Profile Functions ---


async def update_user_profile(
    session: AsyncSession,
    user_id: int,
    update_data: Dict[str, Any],
) -> Optional[User]:
    """Updates a user's profile details (phone, email)."""
    user = await session.get(User, user_id)
    if user:
        for key, value in update_data.items():
            setattr(user, key, value)
        await session.flush()
    return user


# --- Delivery Address Functions ---


async def get_user_addresses(
    session: AsyncSession,
    user_id: int,
) -> List[DeliveryAddress]:
    """Fetches all saved delivery addresses for a specific user."""
    stmt = (
        select(DeliveryAddress)
        .where(DeliveryAddress.user_id == user_id)
        .order_by(DeliveryAddress.id)
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def add_delivery_address(
    session: AsyncSession,
    user_id: int,
    label: str,
    address: str,
) -> DeliveryAddress:
    """Adds a new delivery address for a user."""
    new_address = DeliveryAddress(
        user_id=user_id,
        address_label=label,
        full_address=address,
    )
    session.add(new_address)
    await session.flush()
    return new_address


async def delete_delivery_address(
    session: AsyncSession,
    address_id: int,
    user_id: int,
) -> bool:
    """
    Deletes a delivery address, ensuring it belongs to the correct user.
    """
    address = await session.get(DeliveryAddress, address_id)
    if address and address.user_id == user_id:
        await session.delete(address)
        await session.flush()
        return True
    return False


async def set_default_address(
    session: AsyncSession, user_id: int, address_id: int
) -> Optional[DeliveryAddress]:
    """Sets a specific address as the default for the user."""
    # Step 1: Set all the user's other addresses to is_default = False
    update_stmt = (
        update(DeliveryAddress)
        .where(DeliveryAddress.user_id == user_id, DeliveryAddress.id != address_id)
        .values(is_default=False)
    )
    await session.execute(update_stmt)

    # Step 2: Get the target address and set it as the default
    address_to_set = await session.get(DeliveryAddress, address_id)
    if address_to_set and address_to_set.user_id == user_id:
        address_to_set.is_default = True
        await session.flush()
        return address_to_set
    return None


# -------------------
# Product / Catalog Functions
# -------------------


async def get_categories(session: AsyncSession) -> List[Category]:
    """Fetches all top-level categories."""
    stmt = (
        select(Category)
        .where(Category.parent_id == None)  # noqa: E711
        .order_by(Category.name)
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_category_by_name(session: AsyncSession, name: str) -> Optional[Category]:
    """Fetches a category by its exact name."""
    stmt = select(Category).where(Category.name == name)
    result = await session.execute(stmt)
    return result.scalars().first()


async def create_category(
    session: AsyncSession,
    name: str,
    description: Optional[str] = None,
) -> Category:
    """Creates a new category in the database."""
    new_category = Category(name=name, description=description)
    session.add(new_category)
    await session.flush()
    return new_category


async def delete_category(session: AsyncSession, category_id: int) -> bool:
    """Deletes a category from the database by its ID."""
    category = await session.get(Category, category_id)
    if category:
        await session.delete(category)
        await session.flush()
        return True
    return False


async def get_product(session: AsyncSession, product_id: int) -> Optional[Product]:
    """
    Fetches a single product by its ID, eagerly loading its category.
    """
    stmt = (
        select(Product)
        .where(Product.id == product_id)
        .options(selectinload(Product.category))
    )
    result = await session.execute(stmt)
    return result.scalars().first()


async def get_products_by_category(
    session: AsyncSession, category_id: int
) -> List[Product]:
    """
    Fetches all products within a specific category, eagerly loading their categories.
    """
    stmt = (
        select(Product)
        .where(Product.category_id == category_id)
        .options(selectinload(Product.category))
        .order_by(Product.name)
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def create_product(
    session: AsyncSession,
    name: str,
    description: str,
    price: Decimal,
    stock: int,
    category_id: int,
    image_url: Optional[str] = None,
) -> Product:
    """Creates a new product in the database."""
    new_product = Product(
        name=name,
        description=description,
        price=price,
        stock=stock,
        category_id=category_id,
        image_url=image_url,
    )
    session.add(new_product)
    await session.flush()
    return new_product


async def update_product(
    session: AsyncSession, product_id: int, update_data: Dict[str, Any]
) -> Optional[Product]:
    """
    Updates a product's details and returns the updated object with
    all necessary relationships eagerly loaded for DTO conversion.
    """
    stmt = (
        update(Product)
        .where(Product.id == product_id)
        .values(**update_data)
        .returning(Product.id)
    )
    result = await session.execute(stmt)
    updated_id = result.scalar_one_or_none()
    print(update_data)

    if updated_id:
        return await get_product(session, updated_id)

    return None


async def delete_product(session: AsyncSession, product_id: int) -> bool:
    """Deletes a product from the database by its ID."""
    product = await get_product(session, product_id)
    if product:
        await session.delete(product)
        await session.flush()
        return True
    return False


# -------------------
# Cart Functions
# -------------------


async def get_or_create_cart(session: AsyncSession, user_id: int) -> Cart:
    """
    Retrieves a user's cart, eagerly loading all nested relationships
    (items and their products) needed for DTO conversion.
    Creates a new cart if one doesn't exist.
    """
    stmt = (
        select(Cart)
        .where(Cart.user_id == user_id)
        .options(
            selectinload(Cart.items)
            .selectinload(CartItem.product)
            .selectinload(Product.category)
        )
    )
    result = await session.execute(stmt)
    cart = result.scalars().first()

    if not cart:
        cart = Cart(user_id=user_id)
        session.add(cart)

    return cart


async def get_or_create_cart_lean(session: AsyncSession, user_id: int) -> Cart:
    """
    Retrieves a user's cart without any eager loading.
    Creates a new cart if one doesn't exist.
    This is optimized for operations that only need the cart ID.
    """
    stmt = select(Cart).where(Cart.user_id == user_id)
    result = await session.execute(stmt)
    cart = result.scalars().first()

    if not cart:
        cart = Cart(user_id=user_id)
        session.add(cart)

    return cart


async def add_item_to_cart(
    session: AsyncSession, cart: Cart, product: Product, quantity: int = 1
) -> CartItem:
    """Adds a product to the cart or updates its quantity if it already exists."""
    stmt = select(CartItem).where(
        CartItem.cart_id == cart.id, CartItem.product_id == product.id
    )
    result = await session.execute(stmt)
    cart_item = result.scalars().first()

    if cart_item:
        cart_item.quantity += quantity
    else:
        cart_item = CartItem(cart_id=cart.id, product_id=product.id, quantity=quantity)
        session.add(cart_item)

    await session.flush()
    return cart_item


async def set_cart_item_quantity(
    session: AsyncSession,
    cart_item_id: int,
    new_quantity: int,
) -> type[CartItem] | None:
    """
    Sets the quantity of a specific cart item.
    If the quantity is 0 or less, the item is deleted.
    """
    cart_item = await session.get(CartItem, cart_item_id)
    if not cart_item:
        return None

    if new_quantity > 0:
        cart_item.quantity = new_quantity
        await session.flush()
        return cart_item
    else:
        # If quantity is 0 or less, delete the item.
        await session.delete(cart_item)
        await session.flush()
        return None


async def clear_cart(session: AsyncSession, cart: Cart) -> None:
    """Removes all items from a user's cart."""
    for item in cart.items:
        await session.delete(item)
    await session.flush()


# -------------------
# Order Functions
# -------------------


async def create_order_with_items(
    session: AsyncSession,
    user_id: int,
    contact_name: str,
    phone: str,
    address: str,
    delivery_method: str,
    items: List[CartItem],
) -> Order:
    """
    Creates an order from cart items and atomically reserves stock.
    This is the core transactional function.
    """
    new_order = Order(
        user_id=user_id,
        order_number=generate_order_number(),
        contact_name=contact_name,
        phone=phone,
        address=address,
        delivery_method=delivery_method,
    )
    session.add(new_order)
    await session.flush()

    for item in items:
        product_id = item.product_id
        quantity = item.quantity

        # Get the product with a pessimistic lock.
        product = await session.get(Product, product_id, with_for_update=True)

        if product is None:
            raise ValueError(f"Product with ID {product_id} not found during checkout.")
        if product.stock < quantity:
            raise ValueError(
                f"Not enough stock for '{product.name}'. "
                f"You requested {quantity}, but only {product.stock} are available."
            )

        new_order_item = OrderItem(
            order_id=new_order.id,
            product_id=product.id,
            quantity=quantity,
            price=product.price,
        )
        session.add(new_order_item)

        product.stock -= quantity

    return new_order


async def get_order(session: AsyncSession, order_id: int) -> Optional[Order]:
    """Fetches a single order by its ID, loading its items."""
    stmt = (
        select(Order)
        .where(Order.id == order_id)
        .options(
            selectinload(Order.user),
            selectinload(Order.items)
            .selectinload(OrderItem.product)
            .selectinload(Product.category),
        )
    )
    result = await session.execute(stmt)
    return result.scalars().first()


async def get_orders_by_user_pk(
    session: AsyncSession,
    user_pk_id: int,
) -> Sequence[Order]:
    """
    Fetches all of a user's orders by their user primary key,
    eagerly loading all nested relationships needed for DTO conversion.
    """
    stmt = (
        select(Order)
        .where(Order.user_id == user_pk_id)
        .options(
            selectinload(Order.user),
            selectinload(Order.items)
            .selectinload(OrderItem.product)
            .selectinload(Product.category),
        )
        .order_by(Order.created_at.desc())
    )
    result = await session.execute(stmt)
    return result.scalars().all()


async def get_orders_by_status(
    session: AsyncSession,
    status: OrderStatus,
) -> Sequence[Order]:
    """Fetches all orders with a specific status."""
    stmt = (
        select(Order)
        .where(Order.status == status)
        .options(
            selectinload(Order.user),
            selectinload(Order.items)
            .selectinload(OrderItem.product)
            .selectinload(Product.category),
        )
        .order_by(Order.created_at.desc())
    )
    result = await session.execute(stmt)
    return result.scalars().all()


async def update_order_status(
    session: AsyncSession,
    order_id: int,
    new_status: OrderStatus,
) -> Optional[Order]:
    """Updates the status of a specific order."""
    order = await get_order(session, order_id)
    if order:
        order.status = new_status
        await session.flush()
    return order


async def increase_product_stock(
    session: AsyncSession,
    product_id: int,
    quantity: int,
) -> Optional[Product]:
    """
    Increases the stock for a given product ID.
    Uses a pessimistic lock to prevent race conditions.
    """
    # Lock the product row to ensure atomic updates
    product = await session.get(Product, product_id, with_for_update=True)
    if product:
        product.stock += quantity
        await session.flush()
    return product

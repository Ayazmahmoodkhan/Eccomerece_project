from sqlalchemy import Column, Integer, String, JSON, Boolean,TIMESTAMP, text, Enum, Date, ForeignKey, Float, DateTime, Text
from app.database import Base
from sqlalchemy.sql import func
from datetime import datetime
import enum
from sqlalchemy.orm import relationship


# Enums
class UserRole(str, enum.Enum):
    admin = "admin"
    user = "user"

class OrderStatus(str, enum.Enum):
    pending = "pending"
    shipped = "shipped"
    delivered = "delivered"
    cancelled = "cancelled"

class PaymentMode(str, enum.Enum):
    credit_card = "Credit Card"
    debit_card = "Debit Card"
    paypal = "PayPal"
    cash_on_delivery = "Cash on Delivery"

class RatingEnum(int, enum.Enum):
    one_star = 1
    two_star = 2
    three_star = 3
    four_star = 4
    five_star = 5

# User Table
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    username = Column(String, nullable=False, unique=True)
    email = Column(String, unique=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    role = Column(Enum(UserRole), default=UserRole.user)

    # Relationships
    profile = relationship("UserProfile", back_populates="user", uselist=False)
    addresses = relationship("Address", back_populates="user")
    products = relationship("Product", back_populates="admin")
    orders = relationship("Order", back_populates="user")
    carts = relationship("Cart", back_populates="user")
    reviews = relationship("Review", back_populates="user")

# User Profile Table
class UserProfile(Base):
    __tablename__ = "user_profiles"
    id = Column(Integer, primary_key=True, index=True, unique=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=True)
    date_birth = Column(Date, nullable=False)
    phone = Column(String, nullable=False)
    age = Column(Integer, nullable=False)
    profile_picture = Column(String, nullable=True)

    user = relationship("User", back_populates="profile")

# Address Table
class Address(Base):
    __tablename__ = "addresses"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    street = Column(String, nullable=False)
    city = Column(String, nullable=False)
    state = Column(String, nullable=False)
    postal_code = Column(String, nullable=False)

    user = relationship("User", back_populates="addresses")

# Category Table
class Category(Base):
    __tablename__ = "categories"
    id = Column(Integer, primary_key=True, index=True)
    category_name = Column(String, nullable=False)
    description = Column(String, nullable=True)

    products = relationship("Product", back_populates="category",cascade="all, delete")

# Product Table
class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    sku = Column(String, nullable=False, unique=True)  # Unique product identifier
    product_name = Column(String, nullable=False)
    description = Column(Text)
    color = Column(String, nullable=True)
    price = Column(Float, nullable=False)
    discount = Column(Float, nullable=False)
    stock = Column(Integer, nullable=False)
    brand = Column(String, nullable=False)
    shipping_time = Column(String, nullable=True)

    category_id = Column(Integer, ForeignKey("categories.id"))
    admin_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))

    # Relationships
    cart_items = relationship("CartItem", back_populates="product")
    category = relationship("Category", back_populates="products")
    admin = relationship("User", back_populates="products")
    reviews = relationship("Review", back_populates="product")
    order_items = relationship("OrderItem", back_populates="product")
    images = relationship("ProductImage", back_populates="product", cascade="all, delete-orphan")


# Product Image Table
class ProductImage(Base):
    __tablename__ = "product_images"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"))
    image_url = Column(String, nullable=False)

    # Relationship
    product = relationship("Product", back_populates="images")


# Cart Table
class Cart(Base):
    __tablename__ = "carts"

    id = Column(Integer, primary_key=True, nullable=False, unique=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=text("NOW()"), nullable=False)
    total_amount = Column(Float, nullable=False)
    grand_total = Column(Float, nullable=False)

    # Relationships
    user = relationship("User", back_populates="carts")
    cart_items = relationship("CartItem", back_populates="cart")


# CartItem Table
class CartItem(Base):
    __tablename__ = "cart_items"

    id = Column(Integer, primary_key=True, nullable=False, unique=True, autoincrement=True)
    cart_id = Column(Integer, ForeignKey("carts.id", ondelete="CASCADE"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    quantity = Column(Integer, nullable=False)
    subtotal = Column(Float, nullable=False)

    # Relationships
    cart = relationship("Cart", back_populates="cart_items")
    product = relationship("Product", back_populates="cart_items")


# Order Table
class Order(Base):
    __tablename__ = "orders"
    
    id = Column(Integer, primary_key=True, index=True)
    order_date = Column(DateTime, nullable=False)
    order_amount = Column(Float, nullable=False)
    shipping_date = Column(DateTime, nullable=True)
    order_status = Column(Enum(OrderStatus), nullable=False)
    is_canceled = Column(Boolean, default=False)
    cancel_reason = Column(String, nullable=True)
    coupon_code = Column(String, nullable=True)
    discount_amount = Column(Float, default=0.0)
    cart_id = Column(Integer, ForeignKey("carts.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    created_timestamp = Column(DateTime, default=func.now())
    updated_timestamp = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    payment = relationship("Payment", back_populates="order", uselist=False)
    user = relationship("User", back_populates="orders")
    order_items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    shipping_details = relationship("ShippingDetails", back_populates="order", uselist=False)
    refunds = relationship("Refund", back_populates="order", cascade="all, delete")


    class Config:
        orm_mode = True

# Order Item Table
class OrderItem(Base):
    __tablename__ = "order_items"
    
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"))
    mrp = Column(Float, nullable=False)
    quantity = Column(Integer, nullable=False)

    # Relationships
    order = relationship("Order", back_populates="order_items")
    product = relationship("Product", back_populates="order_items")

    class Config:
        orm_mode = True


# Review Table
class Review(Base):
    __tablename__ = "reviews"
    review_id = Column(Integer, primary_key=True, index=True)
    description = Column(String, nullable=False)
    rating = Column(Enum(RatingEnum), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at  = Column(DateTime(timezone= True), server_default=func.now())

    product = relationship("Product", back_populates="reviews")
    user = relationship("User", back_populates="reviews")

# Payment Table
# class Payment(Base):
#     __tablename__ = "payments"
#     id = Column(Integer, primary_key=True, index=True)
#     order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
#     payment_mode = Column(Enum(PaymentMode), nullable=False)
#     payment_date = Column(DateTime, nullable=False)

#     orders = relationship("Order", back_populates="payments")


    #searching for payment method and shipping details and use later


class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, nullable=False)
    order_id = Column(Integer, ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, unique=True)
    stripe_payment_intent_id = Column(String, nullable=False, unique=True)
    stripe_customer_id = Column(String, nullable=True)
    payment_method = Column(String, nullable=False)
    currency = Column(String, default="usd")
    amount = Column(Float, nullable=False)
    status = Column(String, default="processing")
    payment_ref = Column(String, nullable=True, unique=True)
    paid_at = Column(TIMESTAMP(timezone=True), nullable=True)
    created_timestamp = Column(TIMESTAMP(timezone=True), server_default=text("now()"))
    updated_timestamp = Column(TIMESTAMP(timezone=True), onupdate=text("now()"))

    order = relationship("Order", back_populates="payment")
    logs = relationship("PaymentLog", back_populates="payment", cascade="all, delete-orphan")

#payment log table    

class PaymentLog(Base):
    __tablename__ = "payment_logs"

    id = Column(Integer, primary_key=True, index=True)
    payment_id = Column(Integer, ForeignKey("payments.id"), nullable=False)
    status = Column(String, nullable=False)  # Make sure this line exists
    message = Column(String, nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=text("now()"))

    payment = relationship("Payment", back_populates="logs")



class ShippingDetails(Base):
    __tablename__ = "shipping_details"
    id = Column(Integer, primary_key=True, nullable=False)
    order_id = Column(
        Integer,
        ForeignKey(column="orders.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
    )
    contact_information = Column(String, nullable=False)
    additional_note = Column(String, nullable=True)
    address = Column(String, nullable=False)
    state = Column(String, nullable=False)
    country = Column(String, nullable=False)
    shipping_date = Column(TIMESTAMP(timezone=True))
    created_timestamp = Column(TIMESTAMP(timezone=True), server_default=text("now()"))
    updated_timestamp = Column(TIMESTAMP(timezone=True), nullable=True)

    order = relationship("Order", back_populates="shipping_details")

# Coupons table
class Coupon(Base):
    __tablename__ = "coupons"
    id = Column(Integer, primary_key=True)
    code = Column(String, unique=True, nullable=False)
    discount_type = Column(Enum("percentage", "fixed", name="discounttype"), nullable=False)
    discount_value = Column(Float, nullable=False)
    is_active = Column(Boolean, default=True)
    expiry_date = Column(DateTime, nullable=True)
    usage_limit = Column(Integer, nullable=True)

# Refunds Table

class Refund(Base):
    __tablename__ = "refunds"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id", ondelete="CASCADE"))
    stripe_refund_id = Column(String, nullable=False)
    amount = Column(Float, nullable=False)
    reason = Column(Text, nullable=True)
    status = Column(String, nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    order = relationship("Order", back_populates="refunds")

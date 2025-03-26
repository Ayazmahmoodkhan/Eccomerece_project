from sqlalchemy import Column, Integer, String, Boolean, Enum, Date, ForeignKey, Float, DateTime, Text
from app.database import Base
import enum
from sqlalchemy.orm import relationship

# Enums
class UserRole(str, enum.Enum):
    admin = "admin"
    user = "user"

class OrderStatus(str, enum.Enum):
    pending = "Pending"
    shipped = "Shipped"
    delivered = "Delivered"
    cancelled = "Cancelled"

class PaymentMode(str, enum.Enum):
    credit_card = "Credit Card"
    debit_card = "Debit Card"
    paypal = "PayPal"
    cash_on_delivery = "Cash on Delivery"

class RatingEnum(str, enum.Enum):
    one_star = "1 Star"
    two_star = "2 Stars"
    three_star = "3 Stars"
    four_star = "4 Stars"
    five_star = "5 Stars"

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
    cart = relationship("Cart", back_populates="user")
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
    sku = Column(String, nullable=False, unique=True)  # Added SKU for unique product identification
    product_name = Column(String, nullable=False)
    description=Column(Text)
    color = Column(String, nullable=True)
    price = Column(Float, nullable=False)
    discount = Column(Float, nullable=False)
    stock = Column(Integer, nullable=False)  
    brand = Column(String, nullable=False)
    shipping_time = Column(String, nullable=True) 
    category_id = Column(Integer, ForeignKey("categories.id"))  
    admin_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    # Relationships
    carts = relationship("Cart", back_populates="product")
    category = relationship("Category", back_populates="products")
    admin = relationship("User", back_populates="products")
    reviews = relationship("Review", back_populates="product")
    order_items = relationship("OrderItem", back_populates="product")
    images = relationship("ProductImage", back_populates="product", cascade="all, delete-orphan")
class ProductImage(Base):
    __tablename__ = "product_images"
    
    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"))
    image_url = Column(String, nullable=False)

    product = relationship("Product", back_populates="images")
# Cart Table
class Cart(Base):
    __tablename__ = "carts"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    product_id = Column(Integer, ForeignKey("products.id"))
    grand_total = Column(Float, nullable=False)
    item_total = Column(Integer, nullable=False)

    product = relationship("Product", back_populates="carts")
    user = relationship("User", back_populates="cart")

# Order Table
class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True, index=True)
    order_date = Column(DateTime, nullable=False)
    order_amount = Column(Float, nullable=False)
    shipping_date = Column(DateTime, nullable=True)
    order_status = Column(Enum(OrderStatus), nullable=False)
    cart_id = Column(Integer, ForeignKey("carts.id"))
    user_id = Column(Integer, ForeignKey("users.id"))

    payments = relationship("Payment", back_populates="orders")
    user = relationship("User", back_populates="orders")
    order_items = relationship("OrderItem", back_populates="order")

# Order Item Table
class OrderItem(Base):
    __tablename__ = "order_items"
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"))
    mrp = Column(Float, nullable=False)
    quantity = Column(Integer, nullable=False)

    order = relationship("Order", back_populates="order_items")
    product = relationship("Product", back_populates="order_items")

# Review Table
class Review(Base):
    __tablename__ = "reviews"
    review_id = Column(Integer, primary_key=True, index=True)
    description = Column(String, nullable=False)
    rating = Column(Enum(RatingEnum), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    product = relationship("Product", back_populates="reviews")
    user = relationship("User", back_populates="reviews")

# Payment Table
class Payment(Base):
    __tablename__ = "payments"
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    payment_mode = Column(Enum(PaymentMode), nullable=False)
    payment_date = Column(DateTime, nullable=False)

    orders = relationship("Order", back_populates="payments")
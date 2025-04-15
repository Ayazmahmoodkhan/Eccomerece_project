from pydantic import BaseModel, EmailStr, Field,HttpUrl, field_validator
from datetime import date,datetime
from enum import Enum
from typing import Optional, List, Any
from app.models import RatingEnum

class UserRoleEnum(str,Enum):
    admin="admin"
    user="user"
class UserCreate(BaseModel):
    name: str = Field(..., min_length=3, max_length=50)
    username: str = Field(..., min_length=3, max_length=25)
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=20)
    confirm_password: str = Field(..., min_length=6, max_length=20)
    role: UserRoleEnum=UserRoleEnum.user

class UserLogin(BaseModel):
    login:str
    password:str


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str
#schemas for address form
class Addressbase(BaseModel):
    street:str
    city:str
    state:str
    postal_code:str
class AddressCreate(Addressbase):
    pass
class AddressUpdate(Addressbase):
    pass
class AddressResponse(Addressbase):
    id:int
    user_id:int
    class Config:
        from_attributes=True
#end
#schema for user profile
class UserProfileBase(BaseModel):
    first_name: str
    last_name: str | None = None
    date_birth: date
    phone: str
    age: int
class UserProfileCreate(UserProfileBase):
    pass  # Naya profile create karne ke liye

class UserProfileUpdate(UserProfileBase):
    pass  # Existing profile update karne ke liye

class UserProfileResponse(UserProfileBase):
    id: int
    user_id: int

    class Config:
        from_attributes=True
#end




# Category Base schema (Common fields)
class CategoryBase(BaseModel):
    category_name: str
    description: Optional[str] = None

class CategoryCreate(CategoryBase):
    pass

class CategoryUpdate(BaseModel):
    category_name: Optional[str] = None
    description: Optional[str] = None

class CategoryResponse(CategoryBase):
    id: int

    class Config:
        from_attributes = True
# Product Schema
# class ProductBase(BaseModel):
#     product_name: str
#     price: float
#     discount: float
#     stock: int
#     brand: str
#     category_id: int
#     description: str
#     color: str
#     shipping_time: str

# class ProductCreate(ProductBase):
#     images: List[str]  # Image URLs as a list of strings

# class ProductResponse(ProductBase):
#     id: int
#     sku: str
#     admin_id: int
#     images: List[str]

#     class Config:
#         from_attributes = True

class ProductBase(BaseModel):
    product_name: str
    price: float
    discount: float
    stock: int
    brand: str
    category_id: int
    description: str
    color: str
    shipping_time: str

class ProductCreate(ProductBase):
    images: List[str]  

class ProductResponse(ProductBase):
    id: int
    sku: str
    images: List[str]  

    @field_validator(
        "product_name", "brand", "description", "color", "shipping_time", mode="before"
    )
    @classmethod
    def remove_extra_quotes(cls, value):
        return value.strip('"') if isinstance(value, str) else value

    class Config:
        from_attributes = True

# Cart Item Schema

class CartItemBase(BaseModel):
    product_id: int
    quantity: int
    subtotal: float

class CartItemCreate(CartItemBase):
    pass

class CartItemResponse(CartItemBase):
    id: int

    class Config:
        from_attributes = True

# Cart Schema

class CartBase(BaseModel):
    user_id: int
    total_amount: float

class CartCreate(CartBase):
    cart_items: List[CartItemCreate]

class CartUpdate(CartBase):
    cart_items: Optional[List[CartItemCreate]] = None

class CartResponse(CartBase):
    id: int
    created_at: datetime
    cart_items: List[CartItemResponse]

    class Config:
        from_attributes = True

# Order Schema Enum

class OrderStatus(str, Enum):
    pending = "pending"
    shipped = "shipped"
    delivered = "delivered"
    cancelled = "cancelled"


# OrderItem Schema
class OrderItemBase(BaseModel):
    product_id: int
    mrp: float
    quantity: int

class OrderItemCreate(OrderItemBase):
    pass

class OrderItem(OrderItemBase):
    id: int

    class Config:
        orm_mode = True

# Order Schema
class OrderBase(BaseModel):
    order_date: datetime
    order_amount: float
    shipping_date: Optional[datetime] = None
    order_status: OrderStatus

class OrderCreate(OrderBase):
    cart_id: int
    user_id: int
    items: List[OrderItemCreate]  # nested order items

class OrderResponse(OrderBase):
    id: int
    created_timestamp: datetime
    updated_timestamp: datetime
    items: List[OrderItem] = Field(..., alias="order_items")

    class Config:
        orm_mode = True
        allow_population_by_field_name = True 

class OrderUpdate(BaseModel):
    order_date: Optional[datetime] = None
    order_amount: Optional[float] = None
    shipping_date: Optional[datetime] = None
    order_status: Optional[OrderStatus] = None

    class Config:
        orm_mode = True


# reviews schema
class ReviewBase(BaseModel):
    description: str
    rating: RatingEnum 

class ReviewCreate(ReviewBase):
    product_id: int
    user_id: int

class ReviewResponse(ReviewBase):
    review_id: int
    product_id: int
    user_id: int

    class Config:
        orm_mode = True

# schema for pyment table

class PaymentBase(BaseModel):
    order_id: int
    stripe_payment_intent_id: str
    stripe_customer_id: Optional[str] = None
    payment_method: str
    currency: Optional[str] = "usd"
    amount: float
    status: Optional[str] = "processing"
    payment_ref: Optional[str] = None
    paid_at: Optional[datetime] = None

# Create schema
class PaymentCreate(PaymentBase):
    pass

# Response schema
class PaymentResponse(PaymentBase):
    id: int
    created_timestamp: datetime
    updated_timestamp: Optional[datetime]

    class Config:
        orm_mode = True

# schema for payments logs

class PaymentLogBase(BaseModel):
    payment_id: int
    event_type: str
    raw_data: Any  # Accepts JSON (dict)

# Create schema
class PaymentLogCreate(PaymentLogBase):
    pass

# Response schema
class PaymentLogResponse(PaymentLogBase):
    id: int
    created_at: datetime

    class Config:
        orm_mode = True

# shipping details schema 

class ShippingDetailsBase(BaseModel):
    order_id : int
    contact_information: str
    additional_note: Optional[str] = None
    address: str
    state:  str
    country: str
    shipping_date : Optional [str] = None

class ShippingDetailsCreate(ShippingDetailsBase):
    pass

# shipping details update 

class ShippingDetailsUpdate(BaseModel):
    contact_information: Optional[str] = None
    additional_note: Optional[str] = None
    address: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    shipping_date: Optional[datetime] = None

# shipping details response

class ShippingDetailsResponse(ShippingDetailsBase):
    id : int
    created_timestamp: datetime
    updated_timestamp: Optional[datetime]

    class config:
        orm_mode: True




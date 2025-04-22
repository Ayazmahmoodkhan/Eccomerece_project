from pydantic import BaseModel, EmailStr, Field,HttpUrl, field_validator
from datetime import date,datetime
from enum import Enum
from typing import Optional, List, Any, Literal
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
    username:str
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
    pass  

class UserProfileUpdate(UserProfileBase):
    pass  

class UserProfileResponse(UserProfileBase):
    id: int
    user_id: int

    class Config:
        from_attributes=True
#end




# Category Base schema 
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



# #  Cart Item Schemas 

# class CartItemBase(BaseModel):
#     product_id: int
#     quantity: int

# class CartItemCreate(CartItemBase):
#     pass

# class CartItemResponse(CartItemBase):
#     id: int
#     subtotal: float 

#     class Config:
#         from_attributes = True


# #  Cart Schemas

# class CartCreate(BaseModel):
#     cart_items: List[CartItemCreate]

# class CartUpdate(BaseModel):
#     cart_items: Optional[List[CartItemCreate]] = None

# class CartResponse(BaseModel):
#     id: int
#     total_amount: float 
#     grand_total: float  
#     created_at: datetime
#     cart_items: List[CartItemResponse]

#     class Config:
#         from_attributes = True



# Order Enum

class OrderStatus(str, Enum):
    pending = "pending"
    shipped = "shipped"
    delivered = "delivered"
    cancelled = "cancelled"


# OrderItem Response
class OrderItem(BaseModel):
    id: int
    product_id: int
    mrp: float
    quantity: int

    class Config:
        orm_mode = True

# Order Create 
class OrderCreate(BaseModel):
    cart_id: int
    coupon_code: Optional[str] = None

# Order Response
class OrderResponse(BaseModel):
    id: int
    order_date: datetime
    order_amount: float
    discount_amount: Optional[float]
    shipping_date: Optional[datetime]
    order_status: OrderStatus
    created_timestamp: datetime
    updated_timestamp: datetime
    cart_id: int
    items: List[OrderItem] = Field(..., alias="order_items")

    class Config:
        orm_mode = True
        allow_population_by_field_name = True
 # Order Update
class OrderUpdate(BaseModel):
    order_date: Optional[datetime] = None
    order_amount: Optional[float] = None
    shipping_date: Optional[datetime] = None
    order_status: Optional[OrderStatus] = None

    class Config:
        orm_mode = True

# Apply Coupon
class ApplyCouponRequest(BaseModel):
    coupon_code: str

# Coupon Schemas
class CouponBase(BaseModel):
    code: str
    discount_type: Literal["percentage", "fixed"]
    discount_value: float
    expiry_date: Optional[datetime] = None
    usage_limit: Optional[int] = None

class CouponCreate(CouponBase):
    pass

class CouponResponse(CouponBase):
    id: int
    is_active: bool

    class Config:
        orm_mode = True


# reviews schema
class ReviewCreate(BaseModel):
    product_id: int
    rating: int
    description: str

class ReviewResponse(BaseModel):
    review_id: int
    product_id: int
    user_id: int
    rating: int
    description: str
    created_at: datetime

    class Config:
        orm_mode = True

# schema for pyment table

class PaymentMode(str, Enum):
    credit_card = "Credit Card"
    debit_card = "Debit Card"
    paypal = "PayPal"
    cash_on_delivery = "Cash on Delivery"


class PaymentBase(BaseModel):
    order_id: int
    stripe_payment_intent_id: Optional[str] = None
    stripe_customer_id: Optional[str] = None
    payment_method: PaymentMode
    currency: Optional[str] = "usd"
    amount: float
    status: Optional[str] = "processing"
    payment_ref: Optional[str] = None
    paid_at: Optional[datetime] = None


class PaymentCreate(PaymentBase):
    pass

class PaymentIntentRequest(BaseModel):
    amount: float
    currency: str = "usd"
    payment_method: PaymentMode 
    metadata: Optional[dict] = None
    order_id: int

class PaymentResponse(PaymentBase):
    id: int
    created_timestamp: datetime
    updated_timestamp: Optional[datetime]

    class Config:
        orm_mode = True

# schema for payments logs

class PaymentLogCreate(BaseModel):
    payment_id: int
    status: str
    message: Optional[str] = None


class PaymentLogResponse(PaymentLogCreate):
    id: int
    timestamp: datetime

    class Config:
        orm_mode = True

# Refund Payments Schema


class RefundResponse(BaseModel):
    id: int
    order_id: int
    stripe_refund_id: str
    amount: float
    reason: str | None = None
    status: str
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




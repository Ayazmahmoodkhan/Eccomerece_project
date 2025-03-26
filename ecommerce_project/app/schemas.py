from pydantic import BaseModel, EmailStr, Field,HttpUrl
from datetime import date,datetime
from enum import Enum
from typing import Optional
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



class OrderStatus(str, Enum):
    pending = "pending"
    shipped = "shipped"
    delivered = "delivered"
    cancelled = "cancelled"

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
class ProductBase(BaseModel):
    product_name: str
    image_url: Optional[HttpUrl] = None
    price: float
    discount: float
    stock: int  # Integer for better stock tracking
    brand: str
    category_id: int

class ProductCreate(ProductBase):
    pass

class ProductUpdate(ProductBase):
    pass

class ProductResponse(ProductBase):
    id: int
    class Config:
        from_attributes = True

# Cart Schema
class CartBase(BaseModel):
    user_id: int
    product_id: int
    grand_total: float
    item_total: int

class CartCreate(CartBase):
    pass

class CartUpdate(CartBase):
    pass

class CartResponse(CartBase):
    id: int
    class Config:
        from_attributes = True

# Order Schema
class OrderBase(BaseModel):
    order_date: datetime
    order_amount: float
    shipping_date: Optional[datetime] = None
    order_status: OrderStatus
    cart_id: int
    user_id: int

class OrderCreate(OrderBase):
    pass

class OrderUpdate(OrderBase):
    pass

class OrderResponse(OrderBase):
    id: int
    class Config:
        from_attributes = True
        
class OrderItemSchema(BaseModel):
    id: Optional[int] = None
    order_id: int
    product_id: int
    mrp: float
    quantity: int

    class Config:
        from_attributes = True 

class ReviewBase(BaseModel):
    description: str
    rating: str  # ENUM (1-5) as string

class ReviewCreate(ReviewBase):
    product_id: int
    customer_id: int

class ReviewResponse(ReviewBase):
    review_id: int
    product_id: int
    customer_id: int

    class Config:
        orm_mode = True
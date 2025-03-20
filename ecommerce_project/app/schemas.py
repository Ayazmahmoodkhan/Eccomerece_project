from pydantic import BaseModel, EmailStr, Field
from datetime import date
from enum import Enum

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
    postel_code:str
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
    date_of_birth: date
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
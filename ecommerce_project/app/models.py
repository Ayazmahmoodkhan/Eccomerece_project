from sqlalchemy import Column, Integer, String, Boolean ,Enum, Date, ForeignKey
from app.database import Base
import enum
from sqlalchemy.orm import relationship
class UserRole(str,enum.Enum):
    admin="admin"
    user="user"

class User(Base):
    __tablename__="users"
    id=Column(Integer, primary_key=True,index=True)
    name=Column(String, nullable=False)
    username=Column(String, nullable=False, unique=True)
    email=Column(String,unique=True, nullable=False)
    hashed_password=Column(String,nullable=False)
    is_active=Column(Boolean, default=True)
    role=Column(Enum(UserRole,default=UserRole.user))
    #One-to-One Relationship with UserProfile
    profile=relationship("UserProfile", back_populates="user", uselist=False)
    #One-to-Many Relationship with Address
    addresses=relationship("Address", back_populates="user")

class UserProfile(Base):
    __tablename__="userprofile"
    id=Column(Integer, primary_key=True, index=True, unique=True)
    user_id=Column(Integer, ForeignKey("users.id"), unique=True)
    first_name=Column(String, nullable=False)
    last_name=Column(String, nullable=True)
    date_birth=Column(Date, nullable=False)
    phone=Column(String, nullable=False)
    age=Column(Integer, nullable=False)
    user=relationship("User", back_populates="profile")
class Address(Base):
    __tablename__="address"
    id=Column(Integer,primary_key=True, index=True)
    user_id=Column(Integer, ForeignKey("users.id"), nullable=False)
    street=Column(String, nullable=False)
    city=Column(String,nullable=False)
    state=Column(String,nullable=False)
    postal_code=Column(String,nullable=False)
    user=relationship("User", back_populates="addresses") 
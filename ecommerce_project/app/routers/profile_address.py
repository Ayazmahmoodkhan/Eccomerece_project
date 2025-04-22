from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.models import UserProfile, Address
from app.schemas import  AddressCreate, AddressUpdate, UserProfileCreate, UserProfileUpdate
from app.database import get_db
from app.auth import get_current_user

router = APIRouter()

#  Get User Profile
@router.get("/profile")
def get_my_profile(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    profile = db.query(UserProfile).filter(UserProfile.user_id == current_user.id).first()
    if not profile:
        return {"message": "Profile not found"}
    return profile

# Create Profile
@router.post("/profile", status_code=status.HTTP_201_CREATED)
def create_profile(profile_data: UserProfileUpdate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    existing_profile = db.query(UserProfile).filter(UserProfile.user_id == current_user.id).first()
    if existing_profile:
        raise HTTPException(status_code=400, detail="Profile already exists.")
    profile = UserProfile(**profile_data.model_dump(), user_id=current_user.id)
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile

# Update Profile
@router.put("/profile", status_code=status.HTTP_200_OK)
def update_profile(profile_data: UserProfileUpdate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    profile = db.query(UserProfile).filter(UserProfile.user_id == current_user.id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found.")
    for key, value in profile_data.model_dump(exclude_unset=True).items():
        setattr(profile, key, value)
    db.commit()
    db.refresh(profile)
    return profile

# Get Address
@router.get("/address")
def get_my_address(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    address = db.query(Address).filter(Address.user_id == current_user.id).all()
    if not address:
        return {"message": "Address not found"}
    return address

# Add Address (Max 2 Allowed)
@router.post("/address", status_code=status.HTTP_201_CREATED)
def add_address(address_data: AddressCreate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    existing_addresses = db.query(Address).filter(Address.user_id == current_user.id).count()
    if existing_addresses >= 2:
        raise HTTPException(status_code=400, detail="You can only add up to 2 addresses.")
    address = Address(**address_data.model_dump(), user_id=current_user.id)
    db.add(address)
    db.commit()
    db.refresh(address)
    return address

#Update Address
@router.put("/address", status_code=status.HTTP_200_OK)
def update_address(address_data: AddressUpdate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    address = db.query(Address).filter(Address.user_id == current_user.id).first()
    
    if not address:
        raise HTTPException(status_code=404, detail="Address not found.")

    for key, value in address_data.model_dump(exclude_unset=True).items():
        setattr(address, key, value)

    db.commit()
    db.refresh(address)
    return address

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from models import UserProfile, Address
from schemas import ProfileCreate, ProfileUpdate, AddressCreate, AddressUpdate
from database import get_db
from auth import get_current_user

router = APIRouter()

#  Get User Profile
@router.get("/me/profile")
def get_my_profile(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    profile = db.query(UserProfile).filter(UserProfile.user_id == current_user.id).first()
    if not profile:
        return {"message": "Profile not found"}
    return profile

# Create Profile
@router.post("/me/profile", status_code=status.HTTP_201_CREATED)
def create_profile(profile_data: ProfileCreate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    existing_profile = db.query(UserProfile).filter(UserProfile.user_id == current_user.id).first()
    if existing_profile:
        raise HTTPException(status_code=400, detail="Profile already exists.")

    profile = UserProfile(**profile_data.model_dump(), user_id=current_user.id)
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile

# Update Profile
@router.put("/me/profile", status_code=status.HTTP_200_OK)
def update_profile(profile_data: ProfileUpdate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    profile = db.query(UserProfile).filter(UserProfile.user_id == current_user.id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found.")

    for key, value in profile_data.model_dump(exclude_unset=True).items():
        setattr(profile, key, value)

    db.commit()
    db.refresh(profile)
    return profile

# Get Address
@router.get("/me/address")
def get_my_address(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    address = db.query(Address).filter(Address.user_id == current_user.id).all()
    if not address:
        return {"message": "Address not found"}
    return address

# Add Address (Max 2 Allowed)
@router.post("/me/address", status_code=status.HTTP_201_CREATED)
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
@router.put("/me/address/{address_id}", status_code=status.HTTP_200_OK)
def update_address(address_id: int, address_data: AddressUpdate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    address = db.query(Address).filter(Address.id == address_id, Address.user_id == current_user.id).first()
    
    if not address:
        raise HTTPException(status_code=404, detail="Address not found.")

    for key, value in address_data.model_dump(exclude_unset=True).items():
        setattr(address, key, value)

    db.commit()
    db.refresh(address)
    return address

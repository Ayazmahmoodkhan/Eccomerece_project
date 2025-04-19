from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import ShippingDetails
from app.schemas import ShippingDetailsCreate, ShippingDetailsUpdate, ShippingDetailsResponse

router = APIRouter(prefix="/shipping", tags=["Shipping Details"])

@router.post("/", response_model=ShippingDetailsResponse)
def create_shipping(shipping: ShippingDetailsCreate, db: Session = Depends(get_db)):
    new_shipping = ShippingDetails(**shipping.dict())
    db.add(new_shipping)
    db.commit()
    db.refresh(new_shipping)
    return new_shipping

@router.get("/{shipping_id}", response_model=ShippingDetailsResponse)
def get_shipping(shipping_id: int, db: Session = Depends(get_db)):
    shipping = db.query(ShippingDetails).filter(ShippingDetails.id == shipping_id).first()
    if not shipping:
        raise HTTPException(status_code=404, detail="Shipping detail not found")
    return shipping

@router.put("/{shipping_id}", response_model=ShippingDetailsResponse)
def update_shipping(shipping_id: int, update_data: ShippingDetailsUpdate, db: Session = Depends(get_db)):
    shipping = db.query(ShippingDetails).filter(ShippingDetails.id == shipping_id).first()
    if not shipping:
        raise HTTPException(status_code=404, detail="Shipping detail not found")

    for key, value in update_data.dict(exclude_unset=True).items():
        setattr(shipping, key, value)

    db.commit()
    db.refresh(shipping)
    return shipping

@router.delete("/{shipping_id}")
def delete_shipping(shipping_id: int, db: Session = Depends(get_db)):
    shipping = db.query(ShippingDetails).filter(ShippingDetails.id == shipping_id).first()
    if not shipping:
        raise HTTPException(status_code=404, detail="Shipping detail not found")

    db.delete(shipping)
    db.commit()
    return {"detail": "Shipping detail deleted successfully"}

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app import models, schemas
from app.database import get_db
from app.auth import get_current_user


router = APIRouter(prefix="/shipping", tags=["Shipping Details"])

# @router.post("/", response_model=schemas.ShippingDetailsResponse, status_code=status.HTTP_201_CREATED)
# def create_shipping(
#     shipping: schemas.ShippingDetailsCreate,
#     db: Session = Depends(get_db),
#     current_user: models.User = Depends(get_current_user)
# ):
#     new_shipping = models.ShippingDetails(
#         **shipping.model_dump(),
#         user_id=current_user.id
#     )
#     db.add(new_shipping)
#     db.commit()
#     db.refresh(new_shipping)
#     return new_shipping


@router.get("/order/{order_id}", response_model=List[schemas.ShippingDetailsResponse])
def get_shipping_by_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    shippings = db.query(models.ShippingDetails).filter(models.ShippingDetails.order_id == order_id).all()

    if not shippings:
        raise HTTPException(status_code=404, detail="No shipping details found for this order")

    if any(shipping.user_id != current_user.id for shipping in shippings) and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized to access these shipping details")

    return shippings


@router.put("/{shipping_id}", response_model=schemas.ShippingDetailsResponse)
def update_shipping(
    shipping_id: int,
    update_data: schemas.ShippingDetailsUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    shipping = db.query(models.ShippingDetails).filter(models.ShippingDetails.id == shipping_id).first()

    if not shipping:
        raise HTTPException(status_code=404, detail="Shipping detail not found")

    if shipping.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized to update this shipping detail")

    for key, value in update_data.model_dump(exclude_unset=True).items():
        setattr(shipping, key, value)

    db.commit()
    db.refresh(shipping)
    return shipping


@router.delete("/{shipping_id}", status_code=status.HTTP_200_OK)
def delete_shipping(
    shipping_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    shipping = db.query(models.ShippingDetails).filter(models.ShippingDetails.id == shipping_id).first()

    if not shipping:
        raise HTTPException(status_code=404, detail="Shipping detail not found")

    if shipping.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized to delete this shipping detail")

    db.delete(shipping)
    db.commit()
    return {"detail": "Shipping detail deleted successfully"}


from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, selectinload
from typing import List
from app import models, schemas
from app.database import get_db

router = APIRouter(prefix="/orders", tags=["Orders"])

# Create Order with OrderItems
@router.post("/", response_model=schemas.OrderResponse, status_code=status.HTTP_201_CREATED)
def create_order(order_data: schemas.OrderCreate, db: Session = Depends(get_db)):
    new_order = models.Order(
        order_date=order_data.order_date,
        order_amount=order_data.order_amount,
        shipping_date=order_data.shipping_date,
        order_status=order_data.order_status,
        cart_id=order_data.cart_id,
        user_id=order_data.user_id,
    )
    db.add(new_order)
    db.commit()
    db.refresh(new_order)

    for item in order_data.items:
        order_item = models.OrderItem(
            order_id=new_order.id,
            product_id=item.product_id,
            mrp=item.mrp,
            quantity=item.quantity
        )
        db.add(order_item)

    db.commit()

    #Return the order with items loaded
    return db.query(models.Order).options(selectinload(models.Order.order_items)).filter(models.Order.id == new_order.id).first()




# Get all Orders with Items
@router.get("/", response_model=List[schemas.OrderResponse])
def get_all_orders(db: Session = Depends(get_db)):
    return db.query(models.Order).options(selectinload(models.Order.order_items)).all()

# Get single Order by ID with Items
@router.get("/{order_id}", response_model=schemas.OrderResponse)
def get_order(order_id: int, db: Session = Depends(get_db)):
    order = db.query(models.Order)\
              .options(selectinload(models.Order.order_items))\
              .filter(models.Order.id == order_id)\
              .first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order

# Delete Order and associated items
@router.delete("/{order_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_order(order_id: int, db: Session = Depends(get_db)):
    order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    db.query(models.OrderItem).filter(models.OrderItem.order_id == order_id).delete()
    db.delete(order)
    db.commit()
    return {"detail": "Order and related items deleted"}

from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.orm import Session
from typing import List
from app import models, schemas
from app.database import get_db

router = APIRouter(prefix="/orders", tags=["orders"])

# CRUD operations and routes for orders and order items

# Create an order with order items
def create_order_with_items(db: Session, order: schemas.OrderCreate):
    # Create the main order record
    db_order = models.Order(
        order_date=order.order_date,
        order_amount=order.order_amount,
        shipping_date=order.shipping_date,
        order_status=order.order_status,
        user_id=order.user_id
    )
    db.add(db_order)
    db.commit()
    db.refresh(db_order)

    # Create each order item associated with the order
    for item in order.order_items:
        db_order_item = models.OrderItem(
            order_id=db_order.id,
            product_id=item.product_id,
            quantity=item.quantity,
            price=item.price
        )
        db.add(db_order_item)
    
    db.commit()
    return db_order

# Get all orders
def get_orders(db: Session):
    return db.query(models.Order).all()

# Get a specific order by ID
def get_order_by_id(db: Session, order_id: int):
    return db.query(models.Order).filter(models.Order.id == order_id).first()

# Update an order
def update_order(db: Session, order_id: int, order: schemas.OrderUpdate):
    db_order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if db_order:
        for key, value in order.dict(exclude_unset=True).items():
            setattr(db_order, key, value)
        db.commit()
        db.refresh(db_order)
        return db_order
    return None

# Delete an order
def delete_order(db: Session, order_id: int):
    db_order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if db_order:
        db.delete(db_order)
        db.commit()
        return True
    return False

# Create an order item
def create_order_item(db: Session, order_item: schemas.OrderItemCreate):
    db_order_item = models.OrderItem(**order_item.dict())
    db.add(db_order_item)
    db.commit()
    db.refresh(db_order_item)
    return db_order_item

# Get order items for a specific order
def get_order_items_by_order(db: Session, order_id: int):
    return db.query(models.OrderItem).filter(models.OrderItem.order_id == order_id).all()

# Update an order item
def update_order_item(db: Session, order_item_id: int, order_item: schemas.OrderItemUpdate):
    db_order_item = db.query(models.OrderItem).filter(models.OrderItem.id == order_item_id).first()
    if db_order_item:
        for key, value in order_item.dict(exclude_unset=True).items():
            setattr(db_order_item, key, value)
        db.commit()
        db.refresh(db_order_item)
        return db_order_item
    return None

# Delete an order item
def delete_order_item(db: Session, order_item_id: int):
    db_order_item = db.query(models.OrderItem).filter(models.OrderItem.id == order_item_id).first()
    if db_order_item:
        db.delete(db_order_item)
        db.commit()
        return True
    return False

# Route to create an order with order items
@router.post("/", response_model=schemas.Order, status_code=status.HTTP_201_CREATED)
def create_order_route(order: schemas.OrderCreate, db: Session = Depends(get_db)):
    db_order = create_order_with_items(db=db, order=order)
    return db_order

# Route to get all orders
@router.get("/", response_model=List[schemas.Order])
def get_orders_route(db: Session = Depends(get_db)):
    return get_orders(db=db)

# Route to get a specific order by ID
@router.get("/{order_id}", response_model=schemas.Order)
def get_order_route(order_id: int, db: Session = Depends(get_db)):
    db_order = get_order_by_id(db=db, order_id=order_id)
    if db_order is None:
        raise HTTPException(status_code=404, detail="Order not found")
    return db_order

# Route to update an order
@router.put("/{order_id}", response_model=schemas.Order)
def update_order_route(order_id: int, order: schemas.OrderUpdate, db: Session = Depends(get_db)):
    db_order = update_order(db=db, order_id=order_id, order=order)
    if db_order is None:
        raise HTTPException(status_code=404, detail="Order not found")
    return db_order

# Route to delete an order
@router.delete("/{order_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_order_route(order_id: int, db: Session = Depends(get_db)):
    success = delete_order(db=db, order_id=order_id)
    if not success:
        raise HTTPException(status_code=404, detail="Order not found")
    return {"detail": "Order deleted successfully"}

# Route to create an order item
@router.post("/items", response_model=schemas.OrderItem, status_code=status.HTTP_201_CREATED)
def create_order_item_route(order_item: schemas.OrderItemCreate, db: Session = Depends(get_db)):
    db_order_item = create_order_item(db=db, order_item=order_item)
    return db_order_item

# Route to get order items for a specific order
@router.get("/{order_id}/items", response_model=List[schemas.OrderItem])
def get_order_items_route(order_id: int, db: Session = Depends(get_db)):
    return get_order_items_by_order(db=db, order_id=order_id)

# Route to update an order item
@router.put("/items/{order_item_id}", response_model=schemas.OrderItem)
def update_order_item_route(order_item_id: int, order_item: schemas.OrderItemUpdate, db: Session = Depends(get_db)):
    db_order_item = update_order_item(db=db, order_item_id=order_item_id, order_item=order_item)
    if db_order_item is None:
        raise HTTPException(status_code=404, detail="Order item not found")
    return db_order_item

# Route to delete an order item
@router.delete("/items/{order_item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_order_item_route(order_item_id: int, db: Session = Depends(get_db)):
    success = delete_order_item(db=db, order_item_id=order_item_id)
    if not success:
        raise HTTPException(status_code=404, detail="Order item not found")
    return {"detail": "Order item deleted successfully"}

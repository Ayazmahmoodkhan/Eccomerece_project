from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, selectinload
from typing import List
from datetime import datetime
from app import models, schemas
from app.database import get_db
import stripe

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

# Cancel Order 

@router.put("/cancel/{order_id}")
def cancel_order(order_id: int, db: Session = Depends(get_db)):
    order = db.query(models.Order).filter(models.Order.id == order_id).first()

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.status == "cancelled":
        raise HTTPException(status_code=400, detail="Order already cancelled")

    order.status = "cancelled"
    db.commit()

    # Auto-refund logic here
    if order.stripe_payment_intent_id: 
        try:
            refund = stripe.Refund.create(
                payment_intent=order.stripe_payment_intent_id,
                amount=order.total_price * 100 
            )

            refund_record = models.Refund(
                order_id=order.id,
                stripe_refund_id=refund.id,
                amount=order.total_price,
                reason="Order cancelled",
                status=refund.status
            )
            db.add(refund_record)
            db.commit()
        except stripe.error.StripeError as e:
            raise HTTPException(status_code=500, detail=f"Stripe error: {e.user_message}")

    return {"message": "Order cancelled and refund processed if paid."}

# Checking Refund Record

@router.get("/refunds/{order_id}", response_model=List[schemas.RefundResponse])
def get_refunds(order_id: int, db: Session = Depends(get_db)):
    refunds = db.query(models.Refund).filter(models.Refund.order_id == order_id).all()
    return refunds

# Applying Coupon in Order

@router.put("/orders/{order_id}/apply-coupon")
def apply_coupon(order_id: int, request: schemas.ApplyCouponRequest, db: Session = Depends(get_db)):
    order = db.query(models.Order).filter(models.Order.id == order_id).first()
    coupon = db.query(models.Coupon).filter(models.Coupon.code == request.coupon_code, models.Coupon.is_active == True).first()

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if not coupon:
        raise HTTPException(status_code=400, detail="Invalid or inactive coupon")

    now = datetime.utcnow()
    if coupon.expiry_date and coupon.expiry_date < now:
        raise HTTPException(status_code=400, detail="Coupon expired")

    if coupon.discount_type == "percentage":
        discount = order.order_amount * (coupon.discount_value / 100)
    else:
        discount = coupon.discount_value

    order.coupon_code = coupon.code
    order.discount_amount = min(discount, order.order_amount)
    order.order_amount -= order.discount_amount

    db.commit()
    db.refresh(order)
    return {"message": "Coupon applied", "discount": order.discount_amount}


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

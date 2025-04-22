from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, selectinload
from typing import List
from datetime import datetime
from app import models, schemas
from app.database import get_db
from app.auth import get_current_user
import stripe

router = APIRouter(prefix="/orders", tags=["Orders"])

#  Create Order 
@router.post("/", response_model=schemas.OrderResponse, status_code=status.HTTP_201_CREATED)
def create_order(
    order_data: schemas.OrderCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    cart = db.query(models.Cart).options(selectinload(models.Cart.cart_items)).filter(
        models.Cart.id == order_data.cart_id,
        models.Cart.user_id == current_user.id
    ).first()

    if not cart:
        raise HTTPException(status_code=404, detail="Cart not found or access denied.")

    order_amount = cart.grand_total
    discount_amount = 0

    if order_data.coupon_code:
        coupon = db.query(models.Coupon).filter(
            models.Coupon.code == order_data.coupon_code,
            models.Coupon.is_active == True
        ).first()

        if not coupon:
            raise HTTPException(status_code=400, detail="Invalid or inactive coupon")

        if coupon.expiry_date and coupon.expiry_date < datetime.utcnow():
            raise HTTPException(status_code=400, detail="Coupon expired")

        if coupon.discount_type == "percentage":
            discount_amount = order_amount * (coupon.discount_value / 100)
        else:
            discount_amount = coupon.discount_value

        if discount_amount > order_amount:
            discount_amount = order_amount

        order_amount -= discount_amount

    new_order = models.Order(
        order_date=datetime.utcnow(),
        order_amount=order_amount,
        discount_amount=discount_amount,
        shipping_date=None,
        order_status="pending",
        cart_id=cart.id,
        user_id=current_user.id,
        coupon_code=order_data.coupon_code
    )
    db.add(new_order)
    db.commit()
    db.refresh(new_order)

    for item in cart.cart_items:
        order_item = models.OrderItem(
            order_id=new_order.id,
            product_id=item.product_id,
            mrp=item.subtotal,
            quantity=item.quantity
        )
        db.add(order_item)

    db.commit()

    return db.query(models.Order).options(selectinload(models.Order.order_items)).filter(
        models.Order.id == new_order.id
    ).first()

#  Get All Orders 
@router.get("/", response_model=List[schemas.OrderResponse])
def get_all_orders(db: Session = Depends(get_db)):
    return db.query(models.Order).options(selectinload(models.Order.order_items)).all()

#  Get Single Order 
@router.get("/{order_id}", response_model=schemas.OrderResponse)
def get_order(order_id: int, db: Session = Depends(get_db)):
    order = db.query(models.Order).options(selectinload(models.Order.order_items)).filter(
        models.Order.id == order_id
    ).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order

#  Cancel Order 
@router.put("/cancel/{order_id}")
def cancel_order(order_id: int, db: Session = Depends(get_db)):
    order = db.query(models.Order).filter(models.Order.id == order_id).first()

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.order_status == "cancelled":
        raise HTTPException(status_code=400, detail="Order already cancelled")

    order.order_status = "cancelled"
    db.commit()

    if order.stripe_payment_intent_id:
        try:
            refund = stripe.Refund.create(
                payment_intent=order.stripe_payment_intent_id,
                amount=int(order.order_amount * 100)
            )
            refund_record = models.Refund(
                order_id=order.id,
                stripe_refund_id=refund.id,
                amount=order.order_amount,
                reason="Order cancelled",
                status=refund.status
            )
            db.add(refund_record)
            db.commit()
        except stripe.error.StripeError as e:
            raise HTTPException(status_code=500, detail=f"Stripe error: {e.user_message}")

    return {"message": "Order cancelled and refund processed if applicable."}

#  Get Refund Records 
@router.get("/refunds/{order_id}", response_model=List[schemas.RefundResponse])
def get_refunds(order_id: int, db: Session = Depends(get_db)):
    return db.query(models.Refund).filter(models.Refund.order_id == order_id).all()

#  Apply Coupon to Order 
@router.put("/{order_id}/apply-coupon")
def apply_coupon(order_id: int, request: schemas.ApplyCouponRequest, db: Session = Depends(get_db)):
    order = db.query(models.Order).filter(models.Order.id == order_id).first()
    coupon = db.query(models.Coupon).filter(
        models.Coupon.code == request.coupon_code,
        models.Coupon.is_active == True
    ).first()

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

    discount = min(discount, order.order_amount)
    order.discount_amount = discount
    order.order_amount -= discount
    order.coupon_code = coupon.code

    db.commit()
    db.refresh(order)
    return {"message": "Coupon applied", "discount": discount}

#  Delete Order 
@router.delete("/{order_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_order(order_id: int, db: Session = Depends(get_db)):
    order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    db.query(models.OrderItem).filter(models.OrderItem.order_id == order_id).delete()
    db.delete(order)
    db.commit()
    return {"detail": "Order and related items deleted"}

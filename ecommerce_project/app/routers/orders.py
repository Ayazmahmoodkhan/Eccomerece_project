from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, selectinload
from typing import List
from datetime import datetime, timedelta
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

    total_amount = 0
    item_details = []
    max_shipping_days = 0

    for item in order_data.order_items:
        variant = db.query(models.ProductVariant).filter(models.ProductVariant.id == item.variant_id).first()
        if not variant:
            raise HTTPException(status_code=404, detail=f"Variant ID {item.variant_id} not found")

        price = float(variant.price)
        discount_percent = variant.discount or 0
        discounted_price = price * (1 - discount_percent / 100)
        item_total = discounted_price * item.quantity
        total_amount += item_total

        if variant.shipping_time and variant.shipping_time > max_shipping_days:
            max_shipping_days = variant.shipping_time

        item_details.append({
            "product_id": item.product_id,
            "variant_id": item.variant_id,
            "mrp": price,
            "quantity": item.quantity,
            "total_price": round(item_total, 2)
        })

    # ---- Apply coupon if exists ----
    coupon_discount_amount = 0
    coupon_obj = None
    if order_data.coupon_id:
        coupon_obj = db.query(models.Coupon).filter(models.Coupon.id == order_data.coupon_id, models.Coupon.is_active == True).first()
        if not coupon_obj:
            raise HTTPException(status_code=400, detail="Invalid or expired coupon")

        if coupon_obj.discount_type == "percentage":
            coupon_discount_amount = total_amount * (coupon_obj.discount_value / 100)
        elif coupon_obj.discount_type == "fixed":
            coupon_discount_amount = coupon_obj.discount_value

    final_amount = total_amount - coupon_discount_amount
    if final_amount < 0:
        final_amount = 0

    order_date = datetime.utcnow()
    shipping_date = order_date + timedelta(days=max_shipping_days)

    # ---- Create Order ----
    new_order = models.Order(
        order_date=order_date,
        order_amount=round(total_amount, 2),
        shipping_date=shipping_date,
        order_status=order_data.order_status,
        coupon_id=order_data.coupon_id,
        discount_amount=round(coupon_discount_amount, 2),
        final_amount=round(final_amount, 2),
        user_id=current_user.id  
  
    )
    db.add(new_order)
    db.commit()
    db.refresh(new_order)


    # ---- Create Order Items ----
    for item in item_details:
        order_item = models.OrderItem(
            order_id=new_order.id,
            product_id=item["product_id"],
            variant_id=item["variant_id"],
            mrp=item["mrp"],
            quantity=item["quantity"],
            total_price=item["total_price"]
        )
        db.add(order_item)

    db.commit()
    return db.query(models.Order)\
             .options(selectinload(models.Order.order_items))\
             .filter(models.Order.id == new_order.id).first()

#Get all Orders with Items
@router.get("/", response_model=List[schemas.OrderResponse])
def get_all_orders(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    if current_user.role == "admin":
        return db.query(models.Order).options(selectinload(models.Order.order_items)).all()
    else:
        return db.query(models.Order).filter(models.Order.user_id == current_user.id).options(selectinload(models.Order.order_items)).all()
    
# Get single Order by ID with Items
@router.get("/{order_id}", response_model=schemas.OrderResponse)
def get_order(order_id: int, db: Session = Depends(get_db),current_user:models.User=Depends(get_current_user)):
    order = db.query(models.Order)\
              .options(selectinload(models.Order.order_items)).filter(models.Order.id == order_id).first()

    if not order:
        raise HTTPException(status_code=404, detail=f"Order with ID {order_id} not found")
    if current_user.role != "admin":
        if order.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="You are not authorized to view this order")
    
    return order

# Cancel Order 
@router.put("/cancel/{order_id}")
def cancel_order(order_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    order = db.query(models.Order).filter(models.Order.id == order_id).first()
      # Authorization check
    if not current_user.role=="admin" and order.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="You are not allowed to cancel this order")
    
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if order.order_status == "cancelled":
        raise HTTPException(status_code=400, detail="Order already cancelled")

    order.order_status = "cancelled"
    db.commit()


    refund_record = None

    # Auto-refund logic
    if order.payment and order.payment.stripe_payment_intent_id:
        try:
            refund = stripe.Refund.create(
                payment_intent=order.payment.stripe_payment_intent_id,
                amount=int(order.final_amount * 100)  # Using final_amount here
            )
            refund_record = models.Refund(
                order_id=order.id,
                stripe_refund_id=refund.id,

                amount=order.final_amount,

                reason="Order cancelled",
                status=refund.status
            )
            db.add(refund_record)
            db.commit()
        except stripe.error.StripeError as e:
            raise HTTPException(status_code=500, detail=f"Stripe error: {e.user_message}")


    return {
        "message": "Order cancelled successfully",
        "refund_status": refund_record.status if refund_record else "No payment found"
    }

# Checking Refund Record
@router.get("/refunds/{order_id}", response_model=List[schemas.RefundResponse])
def get_refunds(order_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    refunds = db.query(models.Refund).filter(models.Refund.order_id == order_id).all()

    if not refunds:
        raise HTTPException(status_code=404, detail="No refunds found for this order")

    # Optional: Check if user is allowed to view refund (based on order ownership)
    order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    if not current_user.is_admin and order.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="You are not allowed to view refunds for this order")

    return refunds

# Applying Coupon in Order
@router.put("/orders/{order_id}/apply-coupon", status_code=status.HTTP_200_OK)
def apply_coupon(order_id: int, request: schemas.ApplyCouponRequest, db: Session = Depends(get_db)):
    order = db.query(models.Order).filter(models.Order.id == order_id).first()


    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    coupon = db.query(models.Coupon).filter(
        models.Coupon.code == request.coupon_code,
        models.Coupon.is_active == True
    ).first()
    if not coupon:
        raise HTTPException(status_code=400, detail="Invalid or inactive coupon")

    now = datetime.utcnow()
    if coupon.expiry_date and coupon.expiry_date < now:
        raise HTTPException(status_code=400, detail="Coupon expired")

    # Calculate Discount
    if coupon.discount_type == "percentage":
        discount_amount = order.order_amount * (coupon.discount_value / 100)
    else:
        discount_amount = coupon.discount_value


    discount_amount = min(discount_amount, order.order_amount)  # discount zyada na ho order se

    # Update Order
    order.coupon_id = coupon.id  # Link by ID
    order.discount_amount = discount_amount
    order.final_amount = order.order_amount - discount_amount

    db.commit()
    db.refresh(order)

    return {
        "message": "Coupon applied successfully",
        "order_id": order.id,
        "coupon_code": coupon.code,
        "discount_amount": order.discount_amount,
        "final_amount": order.final_amount
    }


#  Delete Order 
@router.delete("/{order_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_order(order_id: int, db: Session = Depends(get_db)):
    order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    db.query(models.OrderItem).filter(models.OrderItem.order_id == order_id).delete(synchronize_session=False)
    db.delete(order)
    db.commit()
    return {"detail": "Order and associated items deleted successfully"}

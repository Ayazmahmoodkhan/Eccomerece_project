from sqlalchemy.orm import selectinload
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, selectinload, joinedload
from typing import List
from datetime import datetime, timedelta
from app import models, schemas
from app.models import Order, User, OrderStatus
from app.database import get_db
from app.auth import get_current_user
import stripe

router = APIRouter(prefix="/orders", tags=["Orders"])


#  Create Order 

@router.post("/", response_model=schemas.OrderResponse, status_code=status.HTTP_201_CREATED)
def create_order_with_shipping(
    order_data: schemas.OrderCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    if not order_data.shipping_details:
        raise HTTPException(status_code=400, detail="Shipping details are required.")

    total_amount = 0
    item_details = []
    max_shipping_days = 0

    for item in order_data.order_items:
        variant = db.query(models.ProductVariant)\
            .options(
                selectinload(models.ProductVariant.product),
                selectinload(models.ProductVariant.images)
            )\
            .filter(models.ProductVariant.id == item.variant_id)\
            .first()

        if not variant:
            raise HTTPException(status_code=404, detail=f"Variant ID {item.variant_id} not found")

        price = float(variant.price)
        discount_percent = variant.discount or 0
        discounted_price = price * (1 - discount_percent / 100)
        item_total = discounted_price * item.quantity
        total_amount += item_total

        if variant.shipping_time and variant.shipping_time > max_shipping_days:
            max_shipping_days = variant.shipping_time

        # Safely get product image
        product_image = variant.images[0].image_url if variant.images else None

        item.product_name = variant.product.product_name
        item.variant_attributes = variant.attributes
        item.variant_image = product_image

        item_details.append({
            "product_id": variant.product.id,
            "variant_id": item.variant_id,
            "mrp": price,
            "quantity": item.quantity,
            "total_price": round(item_total, 2),
            "product_name": item.product_name,
            "variant_attributes": item.variant_attributes,
            "variant_image": item.variant_image
        })

    # Coupon logic
    coupon_discount_amount = 0
    if order_data.coupon_id:
        coupon = db.query(models.Coupon).filter(
            models.Coupon.id == order_data.coupon_id,
            models.Coupon.is_active == True
        ).first()
        if not coupon:
            raise HTTPException(status_code=400, detail="Invalid or expired coupon")

        if coupon.discount_type == "percentage":
            coupon_discount_amount = total_amount * (coupon.discount_value / 100)
        elif coupon.discount_type == "fixed":
            coupon_discount_amount = coupon.discount_value

    final_amount = max(total_amount - coupon_discount_amount, 0)

    order_date = datetime.utcnow()
    shipping_date = order_date + timedelta(days=max_shipping_days)

    # Create Order
    new_order = models.Order(
        order_date=order_date,
        order_amount=round(total_amount, 2),
        shipping_date=shipping_date,
        order_status=order_data.order_status or "pending",
        coupon_id=order_data.coupon_id,
        discount_amount=round(coupon_discount_amount, 2),
        final_amount=round(final_amount, 2),
        user_id=current_user.id
    )
    db.add(new_order)
    db.commit()
    db.refresh(new_order)

    # Create Order Items
    for item in item_details:
        db.add(models.OrderItem(
            order_id=new_order.id,
            product_id=item["product_id"],
            variant_id=item["variant_id"],
            mrp=item["mrp"],
            quantity=item["quantity"],
            total_price=item["total_price"]
        ))

    # Create Shipping Details
    shipping_data = order_data.shipping_details.model_dump()
    shipping_data.pop("shipping_date", None)
    db.add(models.ShippingDetails(
        **shipping_data,
        user_id=current_user.id,
        order_id=new_order.id,
        shipping_date=shipping_date
    ))

    db.commit()

    # Final fetch with details
    created_order = db.query(models.Order)\
        .options(
            selectinload(models.Order.order_items)
            .selectinload(models.OrderItem.variant)
            .selectinload(models.ProductVariant.product),
            selectinload(models.Order.order_items)
            .selectinload(models.OrderItem.variant)
            .selectinload(models.ProductVariant.images),
            selectinload(models.Order.shipping_details)
        )\
        .filter(models.Order.id == new_order.id).first()

    # Attach values to order_items before returning
    for item in created_order.order_items:
        variant = item.variant
        if variant:
            item.product_name = variant.product.product_name
            item.variant_attributes = variant.attributes
            item.variant_image = variant.images[0].image_url if variant.images else None

    return created_order




#Get all Orders with Items


@router.get("/", response_model=List[schemas.OrderResponse])
def get_all_orders(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    query = db.query(models.Order).options(
        selectinload(models.Order.order_items)
            .selectinload(models.OrderItem.variant)
            .selectinload(models.ProductVariant.product),
        selectinload(models.Order.order_items)
            .selectinload(models.OrderItem.variant)
            .selectinload(models.ProductVariant.images),
        joinedload(models.Order.shipping_details) 
    )

    if current_user.role != "admin":
        query = query.filter(models.Order.user_id == current_user.id)

    orders = query.all()

    for order in orders:
        for item in order.order_items:
            variant = item.variant
            if variant:
                item.product_name = variant.product.product_name
                item.variant_attributes = variant.attributes
                item.variant_image = variant.images[0].image_url if variant.images else None

    return orders


    
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
    
    if current_user.role !="admin"  and order.user_id != current_user.id:
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


    discount_amount = min(discount_amount, order.order_amount)  

    # Update Order
    order.coupon_id = coupon.id  
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
def delete_order(order_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if not current_user.role == "admin" and order.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="You are not authorized to delete this order")

    db.query(models.OrderItem).filter(models.OrderItem.order_id == order_id).delete(synchronize_session=False)
    db.delete(order)
    db.commit()
    return {"detail": "Order and associated items deleted successfully"}

@router.put("/{order_id}/status")
def update_order_status(
    order_id: int,
    status: str,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_user)
):
    if not admin.role == "admin":
        raise HTTPException(status_code=403, detail="Only admins can update order status")
    # Convert string to enum safely
    try:
        status_enum = OrderStatus(status.capitalize())
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid order status. Must be one of: Pending, Confirmed, Shipped, Delivered, Cancelled"
        )
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.order_status == status_enum:
        raise HTTPException(status_code=400, detail="Order status is already set to this value")
    order.order_status = status_enum
    db.commit()
    return {"message": f"Order {order_id} status updated to {status_enum.value}"}
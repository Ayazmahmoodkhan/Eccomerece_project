from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from app.models import Order, Payment, Refund, User, RefundStatus, PaymentLog
from app.database import get_db
from app.auth import get_current_user
from app.schemas import RefundRequest, RefundResponse  # Tum bana chuke ho
import stripe, paypalrestsdk, json
router = APIRouter(prefix="/refunds", tags=["Refunds"])

# ------------------------
# 1. User Refund Request
# ------------------------
@router.post("/request", response_model=RefundResponse)
def request_refund(
    data: RefundRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    order = db.query(Order).filter(Order.id == data.order_id, Order.user_id == current_user.id).first()

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    if order.order_status.name not in ["delivered", "shipped"]:
        raise HTTPException(status_code=400, detail="Refund allowed only after delivery/shipping")
    
    if order.created_timestamp < datetime.utcnow() - timedelta(days=15):
        raise HTTPException(status_code=400, detail="15-day refund window expired")

    existing_refund = db.query(Refund).filter(Refund.order_id == order.id).first()
    if existing_refund:
        raise HTTPException(status_code=400, detail="Refund already requested")

    refund = Refund(
        order_id=order.id,
        stripe_refund_id="pending",
        amount=order.final_amount,
        reason=data.reason,
        status="requested"
    )
    db.add(refund)
    db.commit()
    db.refresh(refund)

    return refund

# ------------------------
# 2. Admin Refund Approval
# ------------------------
@router.post("/approve/{refund_id}")
def approve_refund_request(
    refund_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Only admins can approve
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can approve refunds")

    refund = db.query(Refund).filter(Refund.id == refund_id).first()
    if not refund:
        raise HTTPException(status_code=404, detail="Refund request not found")

    if refund.status != RefundStatus.requested:
        raise HTTPException(status_code=400, detail="Refund already processed")

    payment = db.query(Payment).filter(Payment.order_id == refund.order_id).first()
    if not payment:
        raise HTTPException(status_code=404, detail="Payment record not found")

    refund_method = None
    refund_msg = ""

    try:
        # Stripe Refund
        if payment.payment_method in ["Credit Card", "Debit Card"]:
            stripe_refund = stripe.Refund.create(
                payment_intent=payment.stripe_payment_intent_id,
                amount=int(payment.amount * 100)
            )
            refund.stripe_refund_id = stripe_refund.id
            refund_method = "stripe"
            refund_msg = f"Stripe refund successful. Refund ID: {stripe_refund.id}"

        # PayPal Refund
        elif payment.payment_method == "paypal":
            paypal_payment = paypalrestsdk.Payment.find(payment.paypal_payment_intent_id)
            sale = paypal_payment.transactions[0].related_resources[0].sale

            paypal_refund = sale.refund({
                "amount": {
                    "total": str(payment.amount),
                    "currency": payment.currency
                }
            })

            if paypal_refund.success():
                refund.paypal_refund_id = paypal_refund.id
                refund_method = "paypal"
                refund_msg = f"PayPal refund successful. Refund ID: {paypal_refund.id}"
            else:
                raise HTTPException(status_code=400, detail="PayPal refund failed")
        # Manual Refund (Cash on Delivery)
        elif payment.payment_method == "Cash on Delivery":
            refund.refund_method = "manual"
            refund_method = "manual"
            refund_msg = "Manual refund initiated for COD payment"

        else:
            raise HTTPException(status_code=400, detail="Unsupported payment method")

        # Update refund record
        refund.status = RefundStatus.approved
        refund.refunded_by = current_user.id
        refund.refunded_at = datetime.utcnow()
        db.commit()

        # Log refund in PaymentLog (optional but recommended)
        log = PaymentLog(
            payment_id=payment.id,
            status="refund_approved",
            message=refund_msg
        )
        db.add(log)
        db.commit()

        return {"message": f"Refund approved via {refund_method}", "status": "success"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Refund approval failed end: {str(e)}")

# ------------------------
# 3. User or Admin: List My Refunds
# ------------------------
@router.get("/my-requests", response_model=list[RefundResponse])
def list_my_refunds(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):  
    if current_user.role == "user":
        refunds = db.query(Refund).join(Order).filter(Order.user_id == current_user.id).all()
    elif current_user.role == "admin":
        refunds = db.query(Refund).all()
    else:
        raise HTTPException(status_code=403, detail="Unauthorized access")
    
    return refunds

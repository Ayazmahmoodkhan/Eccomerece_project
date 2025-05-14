from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Payment, PaymentLog, Order, User, OrderStatus, Order, User, OrderStatus
from app.schemas import PaymentCreate, PaymentResponse, PaymentLogCreate, PaymentIntentRequest, PaymentMode, StripeCheckoutResponse
from app.config import Settings
from app.auth import get_current_user, StripeCheckoutResponse
import paypalrestsdk
from app.auth import get_current_user
from app.routers.admin import PaymentMethod
import stripe, paypalrestsdk

router = APIRouter(prefix="/payments", tags=["Payments"])

# Configure PayPal SDK
paypalrestsdk.configure({
    "mode": "sandbox",  # Set to "live" for production
    "client_id": settings.paypal_client_id,  
    "client_secret": settings.paypal_client_secret
})
# Configure Stripe SDK
stripe.api_key = settings.stripe_secret_key

# Endpoint to create payment session
@router.post("/create-checkout-session/", response_model=StripeCheckoutResponse)
async def create_checkout_session(
    payment_data: PaymentIntentRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        # 1. Check if payment already exists for the order
        existing_payment = db.query(Payment).filter(Payment.order_id == payment_data.order_id).first()
        if existing_payment:
            raise HTTPException(status_code=400, detail="Payment for this order already exists")

        # 2. Fetch the order from DB and validate ownership
        order = db.query(Order).filter(Order.id == payment_data.order_id).first()
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")

        if order.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized to pay for this order")
        if order.order_status != OrderStatus.pending:
            raise HTTPException(status_code=400, detail=f"Your order status is '{order.order_status.value}'")

        # 3. Use order.amount from DB
        amount = order.final_amount
        # Check if selected payment method is enabled
        enabled_method = db.query(PaymentMethod).filter_by(method=payment_data.payment_method, enabled=True).first()
        if not enabled_method:
            raise HTTPException(status_code=403, detail=f"{payment_data.payment_method} is currently disabled by admin")


        # ===== Stripe Payment Handling =====
        if payment_data.payment_method in [PaymentMode.credit_card, PaymentMode.debit_card]:
            # Create Stripe Checkout Session for card payment
            checkout_session = stripe.checkout.Session.create(
                payment_method_types=["card"],
                line_items=[{
                    'price_data': {
                        'currency': payment_data.currency,
                        'product_data': {'name': f"Order #{payment_data.order_id}"},
                        'unit_amount': int(amount * 100),  # Stripe needs amount in cents
                    },
                    'quantity': 1,
                }],
                mode='payment',
                success_url=f"{settings.frontend_url}/success?session_id={{CHECKOUT_SESSION_ID}}",
                cancel_url=f"{settings.frontend_url}/cancel",
                metadata={"order_id": payment_data.order_id},
            )
            # Save payment record for Stripe
            payment = Payment(
                order_id=order.id,
                stripe_payment_intent_id=checkout_session.payment_intent,
                stripe_checkout_session_id=checkout_session.id,
                stripe_customer_id=None,
                paypal_payment_intent_id=None,
                payment_method=payment_data.payment_method.value,
                currency=payment_data.currency,
                amount=amount,
                status="created",
                payment_ref=None
            )

            db.add(payment)
            db.commit()
            db.refresh(payment)

            # Log payment creation in PaymentLog
            log = PaymentLog(
                payment_id=payment.id,
                status="checkout_session_created",
                message=f"Stripe Checkout Session created: {checkout_session.id}"
            )
            db.add(log)
            db.commit()

            return {
                "payment_id": payment.id,
                "order_id": order.id,
                "checkout_url": checkout_session.url,
                "amount": payment.amount,
                "status": payment.status
            }

        # ===== PayPal Payment Handling =====
        elif payment_data.payment_method == PaymentMode.paypal:
            # Create PayPal Payment for PayPal method
            payment_response = paypalrestsdk.Payment({
                "intent": "sale",
                "payer": {
                    "payment_method": "paypal"
                },
                "redirect_urls": {
                    "return_url": f"{settings.frontend_url}/paypal/success?order_id={order.id}",
                    "cancel_url": f"{settings.frontend_url}/paypal/cancel?order_id={order.id}"
                },
                "transactions": [{
                    "item_list": {
                        "items": [{
                            "name": f"Order #{payment_data.order_id}",
                            "sku": "item",
                            "price": str(amount),
                            "currency": payment_data.currency,
                            "quantity": 1
                        }]
                    },
                    "amount": {
                        "total": str(amount),
                        "currency": payment_data.currency
                    },
                    "description": f"Payment for Order #{payment_data.order_id}"
                }]
            })

            if payment_response.create():
                approval_url = next(
                    (link["href"] for link in payment_response.links if link["rel"] == "approval_url"),
                    None
                )

                if not approval_url:
                    raise HTTPException(status_code=400, detail="Unable to generate PayPal approval URL")

                # Save PayPal payment record
                payment = Payment(
                    order_id=order.id,
                    stripe_payment_intent_id=None,          
                    stripe_customer_id=None,                
                    paypal_payment_intent_id=payment_response.id, 
                    payment_method="paypal",
                    currency=payment_data.currency,
                    amount=amount,
                    status="created",
                    payment_ref=None
                )

                db.add(payment)
                db.commit()
                db.refresh(payment)

                # Log payment creation in PaymentLog
                log = PaymentLog(
                    payment_id=payment.id,
                    status="paypal_checkout_created",
                    message="PayPal payment created"
                )
                db.add(log)
                db.commit()

                return {
                    "payment_id": payment.id,
                    "order_id": order.id,
                    "checkout_url": approval_url,
                    "amount": amount,
                    "status": payment.status
                }
            else:
                error_message = payment_response.error.get('message', 'Unknown error')
                raise HTTPException(status_code=500, detail=f"PayPal payment creation failed: {error_message}")

        # ===== COD (Cash on Delivery) Handling =====
        elif payment_data.payment_method == PaymentMode.cash_on_delivery:
            # Handle Cash on Delivery scenario
            payment = Payment(
                order_id=order.id,
                stripe_payment_intent_id=None,
                stripe_customer_id=None,
                payment_method=payment_data.payment_method.value,
                currency=payment_data.currency,
                amount=amount,
                status="pending",
                payment_ref=None,
                paid_at=None
            )

            db.add(payment)
            db.commit()
            db.refresh(payment)

            log = PaymentLog(
                payment_id=payment.id,
                status="cash_on_delivery_created",
                message="COD order created successfully"
            )
            db.add(log)
            db.commit()

            return {"message": "Cash on Delivery order created. Pay upon delivery."}

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{payment_id}", response_model=PaymentResponse)
def get_payment(payment_id: int, db: Session = Depends(get_db)):
    payment = db.query(Payment).filter(Payment.id == payment_id).first()
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    return payment

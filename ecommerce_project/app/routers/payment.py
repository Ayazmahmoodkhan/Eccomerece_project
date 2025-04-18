from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.database import get_db
from app.models import Payment, PaymentLog
from app.schemas import PaymentCreate, PaymentResponse, PaymentLogCreate, PaymentIntentRequest, PaymentMode
import stripe
from app.config import settings

router = APIRouter(prefix="/payments", tags=["Payments"])

stripe.api_key = settings.stripe_secret_key




# Creating checkout session and logging
@router.post("/create-checkout-session/", response_model=PaymentResponse)
async def create_checkout_session(payment_data: PaymentIntentRequest, db: Session = Depends(get_db)):
    try:
        existing_payment = db.query(Payment).filter(Payment.order_id == payment_data.order_id).first()
        if existing_payment:
            raise HTTPException(status_code=400, detail="Payment for this order already exists")

        if payment_data.payment_method in [PaymentMode.credit_card, PaymentMode.debit_card, PaymentMode.paypal]:
            # 1. Create Stripe Checkout Session
            checkout_session = stripe.checkout.Session.create(
                payment_method_types=["card"],  # Only accepting card payments
                line_items=[
                    {
                        'price_data': {
                            'currency': payment_data.currency,
                            'product_data': {
                                'name': f"Order #{payment_data.order_id}",
                            },
                            'unit_amount': int(payment_data.amount * 100),  # amount in cents
                        },
                        'quantity': 1,
                    },
                ],
                mode='payment',  # The mode should be 'payment' for one-time payments
                success_url=f"{settings.frontend_url}/success?session_id={{CHECKOUT_SESSION_ID}}",  # URL after successful payment
                cancel_url=f"{settings.frontend_url}/cancel",  # URL if the user cancels the payment
                metadata={"order_id": payment_data.order_id},
            )

            # 2. Save payment record in the database with a 'created' status
            payment = Payment(
                order_id=payment_data.order_id,
                stripe_payment_intent_id=checkout_session.id,
                stripe_customer_id=None,  # Stripe will fill this in later
                payment_method=payment_data.payment_method.value,
                currency=payment_data.currency,
                amount=payment_data.amount,
                status="created",  # Initial status before payment
                payment_ref=None,
                paid_at=None
            )

            db.add(payment)
            db.commit()
            db.refresh(payment)

            # 3. Log the payment creation status in the PaymentLog table
            log = PaymentLog(
                payment_id=payment.id,
                status="checkout_session_created",
                message=f"Stripe Checkout Session created with ID: {checkout_session.id}. Redirect user to {checkout_session.url}"
            )
            db.add(log)
            db.commit()

            return payment  # Return the PaymentResponse schema automatically

        elif payment_data.payment_method == PaymentMode.cash_on_delivery:
            # Handle Cash on Delivery (no Stripe involvement)
            payment = Payment(
                order_id=payment_data.order_id,
                stripe_payment_intent_id=None,
                stripe_customer_id=None,
                payment_method=payment_data.payment_method.value,
                currency=payment_data.currency,
                amount=payment_data.amount,
                status="pending",  # Payment status is pending for COD
                payment_ref=None,
                paid_at=None
            )

            db.add(payment)
            db.commit()
            db.refresh(payment)

            # 4. Log the Cash on Delivery order creation in the PaymentLog table
            log = PaymentLog(
                payment_id=payment.id,
                status="cash_on_delivery_created",
                message="Cash on Delivery order created successfully. Awaiting payment upon delivery."
            )
            db.add(log)
            db.commit()

            return {"message": "Cash on Delivery order created successfully. Please pay upon delivery."}

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{payment_id}", response_model=PaymentResponse)
def get_payment(payment_id: int, db: Session = Depends(get_db)):
    payment = db.query(Payment).filter(Payment.id == payment_id).first()
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    return payment
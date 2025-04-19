import stripe
from fastapi import APIRouter, Request, Header, HTTPException, status, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from datetime import datetime

from app.config import settings
from app.database import get_db
from app.models import Payment, Order, User
from app.send_email import send_payment_confirmation

router = APIRouter(prefix="/webhook", tags=["Stripe Webhook"])

# Set your secret key
stripe.api_key = settings.stripe_secret_key


@router.post("/stripe")
async def stripe_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    stripe_signature: str = Header(None),
    db: Session = Depends(get_db),
):
    payload = await request.body()

    try:
        event = stripe.Webhook.construct_event(
            payload=payload,
            sig_header=stripe_signature,
            secret=settings.stripe_webhook_secret
        )
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid Stripe signature")

    if event["type"] == "payment_intent.succeeded":
        intent = event["data"]["object"]
        stripe_payment_intent_id = intent["id"]

        # Get the related payment
        payment = db.query(Payment).filter(Payment.stripe_payment_intent_id == stripe_payment_intent_id).first()

        if payment and payment.status != "succeeded":
            payment.status = "succeeded"
            payment.paid_at = datetime.utcnow()
            db.commit()

            # Fetch related order and user
            order = db.query(Order).filter(Order.id == payment.order_id).first()
            user = db.query(User).filter(User.id == order.user_id).first() if order else None

            # Send payment confirmation email
            if user:
                send_payment_confirmation(
                    background_tasks,
                    email_to=user.email,
                    name=user.name,
                    order_id=payment.order_id,
                    amount=payment.amount
                )

    return {"status": "success"}

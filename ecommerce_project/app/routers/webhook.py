import stripe, os, json
from fastapi import APIRouter, Request, Header, HTTPException, status, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from datetime import datetime

from app.config import settings
from app.database import get_db
from app.models import Payment, Order, User, OrderStatus
from app.send_email import send_payment_confirmation
from dotenv import load_dotenv
router = APIRouter(prefix="/webhook", tags=["Stripe Webhook"])

# Set your secret key
stripe.api_key = settings.stripe_secret_key
load_dotenv()
stripe_webhook_secret= os.getenv("STRIPE_WEBHOOK_SECRET")



@router.post("/")
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
            secret=stripe_webhook_secret
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
            if order:
                order.order_status=OrderStatus.confirmed
            db.commit()
            # Send payment confirmation email
            if user:
                send_payment_confirmation(
                    background_tasks,
                    email_to=user.email,
                    name=user.name,
                    order_id=payment.order_id,
                    amount=payment.amount
                )
        elif event["type"] == "checkout.session.completed":
            session = event["data"]["object"]
            session_id = session["id"]

            # Retrieve full session to access payment_intent
            session = stripe.checkout.Session.retrieve(session_id, expand=["payment_intent"])
            payment_intent_id = session.payment_intent.id

            # Update existing payment record
            payment = db.query(Payment).filter(Payment.stripe_checkout_session_id == session.id).first()
            if payment and not payment.stripe_payment_intent_id:
                payment.stripe_payment_intent_id = payment_intent_id
                db.commit()
    return {"status": "success"}

@router.post("/paypal")
async def paypal_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    try:
        payload = await request.body()
        event = json.loads(payload)

        event_type = event.get("event_type")
        resource = event.get("resource")

        if event_type == "PAYMENT.CAPTURE.COMPLETED":
            capture_id = resource.get("id")
            invoice_id = resource.get("invoice_id")  # You should set this during payment creation

            payment = db.query(Payment).filter(Payment.paypal_payment_id == capture_id).first()

            if payment and payment.status != "succeeded":
                payment.status = "succeeded"
                payment.paid_at = datetime.utcnow()
                db.commit()

                # Update related order
                order = db.query(Order).filter(Order.id == payment.order_id).first()
                user = db.query(User).filter(User.id == order.user_id).first() if order else None

                if order:
                    order.order_status = OrderStatus.confirmed
                    db.commit()

                if user:
                    send_payment_confirmation(
                        background_tasks,
                        email_to=user.email,
                        name=user.name,
                        order_id=payment.order_id,
                        amount=payment.amount
                    )

        return {"status": "success"}

    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Webhook error: {str(e)}")
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
import stripe
from app.config import settings
from app.database import get_db
from app.models import Payment
from app.schemas import PaymentBase

router = APIRouter()
stripe.api_key = settings.stripe_secret_key


class PaymentIntentRequest(BaseModel):
    amount: float
    currency: str = "usd"
    metadata: dict = {}


@router.post("/create-payment")
def create_payment_intent(payment_data: PaymentIntentRequest):
    try:
        intent = stripe.PaymentIntent.create(
            amount=int(payment_data.amount * 100),  # Stripe requires amount in cents
            currency=payment_data.currency,
            metadata=payment_data.metadata
        )
        return {"client_secret": intent.client_secret}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{payment_id}", response_model=PaymentBase)
def get_payment(payment_id: int, db: Session = Depends(get_db)):
    payment = db.query(Payment).filter(Payment.id == payment_id).first()
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    return payment

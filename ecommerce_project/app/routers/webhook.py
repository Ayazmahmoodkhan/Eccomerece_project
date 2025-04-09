from fastapi import APIRouter, Request, Header, HTTPException, Depends
from sqlalchemy.orm import Session
import stripe
from app.config import settings
from app.models import PaymentLog
from app.database import get_db
from datetime import datetime

router = APIRouter()
stripe.api_key = settings.stripe_secret_key

@router.post("/stripe")
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(None),
    db: Session = Depends(get_db)
):
    payload = await request.body()

    try:
        event = stripe.Webhook.construct_event(
            payload=payload,
            sig_header=stripe_signature,
            secret=settings.STRIPE_WEBHOOK_SECRET
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")

    # Save to Payment Logs Table
    db_log = PaymentLog(
        event_id=event.id,
        event_type=event.type,
        payload=payload.decode(),
        received_at=datetime.utcnow()
    )
    db.add(db_log)
    db.commit()

    # Optional: Update Payment Status based on event
    if event["type"] == "payment_intent.succeeded":
        intent = event["data"]["object"]
        print("Payment succeeded for:", intent["id"])
        # you could query Payment table and update status to 'succeeded'

    return {"status": "success"}

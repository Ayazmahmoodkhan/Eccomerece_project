from fastapi import FastAPI, HTTPException, status, Depends, BackgroundTasks
from fastapi_mail import FastMail, MessageSchema
from pydantic import EmailStr
from sqlalchemy.orm import Session
from app.database import get_db, Base , engine
from app.models import User
from app.schemas import UserCreate, UserLogin,ResetPasswordRequest
from app.utils import hash_password, verify_password , pwd_context, create_reset_token, verify_reset_token
from app.auth import create_access_token
from app.send_email import send_email_background
import os
from fastapi.responses import RedirectResponse
from app.routers import profile_address
from app.routers.admin import router as admin_router
from app.routers.categoryroute import router as category_router
from app.routers.productroute import router as product_router
from app.routers.cart import router as cart_router
from app.routers.webhook import router as webhook_router
from app.routers.payment import router as payment_router
from app.routers.orders import router as order_router
from app.routers.reviews import router as review_router
from app.routers.shipping_details import router as shippingdetails_router

app=FastAPI()


Base.metadata.create_all(bind=engine)


#register & login start
@app.post("/register/")
def register(user:UserCreate,background_tasks:BackgroundTasks,db:Session=Depends(get_db)):
    if user.password != user.confirm_password:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Passwords do not match")
    existing_user=db.query(User).filter((User.username==user.username) | (User.email == user.email)).first()
    if existing_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,detail="Username or Email already exists")
    new_user=User(
        name=user.name,
        username=user.username,
        email=user.email,
        hashed_password=hash_password(user.password),
        is_active=True,
        role=user.role
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    background_tasks.add_task(
            send_email_background,background_tasks,
            "Welcome to our platform!",
            new_user.email,
            {"title":"Welcome!","name":new_user.username}
        )
    return {"message":"User registered successfully"}

@app.post("/login/")
def login(user: UserLogin, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(
        (User.username == user.login) | (User.email == user.login)
    ).first()
    if not db_user or not verify_password(user.password, db_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
        )
    if not db_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Your account is inactive"
        )
    # Updated function call (only user_id is passed)
    access_token = create_access_token(db_user.id)

    return {"access_token": access_token, "token_type": "bearer"}

#register & login end

#forgot password reset start
FRONTEND_BASE_URL = os.getenv("FRONTEND_URL", "http://127.0.0.1:5500")
from app.send_email import conf
@app.post("/forgot-password/")
async def forgot_password(email: EmailStr, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """User ko password reset email send karega, token save nahi hoga"""
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="Email not found")
    reset_token = create_reset_token(user.id)
    reset_link = f"http://192.168.1.49:8000/reset-password?token={reset_token}"
    email_body = f"""
    <html>
    <body>
        <h3>Password Reset Request</h3>
        <p>Click the link below to reset your password:</p>
        <a href="{reset_link}">{reset_link}</a>
    </body>
    </html>
    """
    message = MessageSchema(
        subject="Reset Your Password",
        recipients=[email],
        body=email_body,
        subtype="html"
    )
    fm = FastMail(conf)
    background_tasks.add_task(fm.send_message, message)
    return {"message": "Password reset link sent to your email", "token": reset_token}
@app.get("/reset-password/")
async def validate_token(token: str):
    """Token validate karega aur frontend pe redirect karega"""
    if not token:
        raise HTTPException(status_code=400, detail="Token is required")
    frontend_url = f"{FRONTEND_BASE_URL}/reset-password.html?token={token}"
    return RedirectResponse(url=frontend_url)
@app.post("/reset-password/")
async def reset_password(data: ResetPasswordRequest, db: Session = Depends(get_db)):
    """User ka password reset karega"""
    user_id = verify_reset_token(data.token)
    if not user_id:
        raise HTTPException(status_code=400, detail="Invalid or expired token")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.password = hash_password(data.new_password)
    db.commit()
    return {"message": "Password updated successfully"}
#forgot password reset end

# Routers  

app.include_router(profile_address.router, prefix="/user", tags=["User Profile & Address"])
app.include_router(admin_router)
app.include_router(product_router)
app.include_router(category_router)
app.include_router(review_router)
app.include_router(cart_router)
app.include_router(order_router)
app.include_router(shippingdetails_router)
app.include_router(webhook_router)
app.include_router(payment_router)
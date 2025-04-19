from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.schemas import  UserCreate
from app.auth import get_current_user
from app.utils import pwd_context
from typing import List
from app.database import get_db
from app.models import User, Product, Order, Category, Refund
from app.schemas import ProductCreate, OrderUpdate, CategoryResponse, RefundResponse
router=APIRouter()

router = APIRouter(prefix="/admin", tags=["Admin Panel"])
@router.post("/create-admin")
def create_admin(user: UserCreate, db: Session = Depends(get_db), current_user= Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admin can create another admin.")
    existing_admin = db.query(User).filter(User.email == user.email).first()
    if existing_admin:
        raise HTTPException(status_code=400, detail="Admin with this email already exists.")

    hashed_password = pwd_context.hash(user.password)
    new_admin = User(
        username=user.username,
        email=user.email,
        hashed_password=hashed_password,
        role="admin",
        is_active=True
    )

    db.add(new_admin)
    db.commit()
    db.refresh(new_admin)

    return {"message": "Admin account created successfully"}

def admin_required(current_user=Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user

# Admin Profile & Stats
from sqlalchemy import func
@router.get("/admin-profile")
def get_admin_profile(admin: User = Depends(admin_required), db: Session = Depends(get_db)):
    total_products = db.query(Product).count()
    total_orders = db.query(Order).count()
    total_sales = db.query(Order).filter(Order.order_status == "delivered").count()
    total_revenue = db.query(func.sum(Order.order_amount)).filter(Order.order_status == "delivered").scalar()
  #  total_revenue = db.query(Order).filter(Order.order_status == "delivered").with_entities(Order.order_amount).sum()

    return {
        "admin_name": admin.name,
        "total_products": total_products,
        "total_orders": total_orders,
        "total_sales": total_sales,
        "total_revenue": total_revenue
    }
#category 
@router.get("/categories", response_model=list[CategoryResponse])
def get_categories(db: Session = Depends(get_db)):
    categories = db.query(Category).all()
    return categories
#Product Management

#Order Management
@router.get("/orders")
def get_orders(admin: User = Depends(admin_required), db: Session = Depends(get_db)):
    orders = db.query(Order).all()
    return {"orders": orders}

@router.put("/orders/{order_id}")
def update_order_status(order_id: int, order_update: OrderUpdate, admin: User = Depends(admin_required), db: Session = Depends(get_db)):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    order.order_status = order_update.order_status
    db.commit()
    db.refresh(order)
    return {"msg": "Order status updated successfully", "order": order}

# Admins checks refunds 
@router.get("/refunds", response_model=List[RefundResponse])
def get_all_refunds(
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_required)
):
    refunds = db.query(Refund).all()
    return refunds

# # User Management
# @router.get("/users")
# def get_users(admin: User = Depends(admin_required), db: Session = Depends(get_db)):
#     users = db.query(User).filter(User.role == "user").all()
#     return {"users": users}

# @router.put("/users/{user_id}")
# def block_unblock_user(user_id: int, user_update: UserUpdate, admin: User = Depends(admin_required), db: Session = Depends(get_db)):
#     user = db.query(User).filter(User.id == user_id).first()
#     if not user:
#         raise HTTPException(status_code=404, detail="User not found")

#     user.is_active = user_update.is_active
#     db.commit()
#     db.refresh(user)
#     return {"msg": "User status updated", "user": user}

# # Payments & Refunds
# @router.get("/payments")
# def get_payments(admin: User = Depends(admin_required), db: Session = Depends(get_db)):
#     payments = db.query(Payment).all()
#     return {"payments": payments}

# @router.put("/payments/{payment_id}/refund")
# def refund_payment(payment_id: int, refund_data: PaymentRefund, admin: User = Depends(admin_required), db: Session = Depends(get_db)):
#     payment = db.query(Payment).filter(Payment.id == payment_id).first()
#     if not payment:
#         raise HTTPException(status_code=404, detail="Payment not found")

#     payment.refunded = refund_data.refunded
#     db.commit()
#     db.refresh(payment)
#     return {"msg": "Payment refunded successfully", "payment": payment}

#Reports & Analytics
@router.get("/reports")
def get_reports(admin: User = Depends(admin_required), db: Session = Depends(get_db)):
    total_revenue = db.query(func.sum(Order.order_amount)).filter(Order.order_status == "delivered").scalar()
    total_orders = db.query(Order).count()
    total_users = db.query(User).filter(User.role == "user").count()

    return {
        "total_revenue": total_revenue,
        "total_orders": total_orders,
        "total_users": total_users
    }

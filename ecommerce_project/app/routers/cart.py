from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Cart, CartItem, Product
from app.schemas import CartCreate, CartResponse
from typing import List

router = APIRouter(prefix="/carts", tags=["Carts"])

@router.post("/", response_model=CartResponse, status_code=status.HTTP_201_CREATED)
def create_cart(cart_data: CartCreate, db: Session = Depends(get_db)):
    cart = Cart(user_id=cart_data.user_id, total_amount=cart_data.total_amount)
    db.add(cart)
    db.commit()
    db.refresh(cart)

    for item in cart_data.cart_items:
        # Optional: validate product existence
        product = db.query(Product).filter(Product.id == item.product_id).first()
        if not product:
            raise HTTPException(status_code=404, detail=f"Product ID {item.product_id} not found.")

        cart_item = CartItem(
            cart_id=cart.id,
            product_id=item.product_id,
            quantity=item.quantity,
            subtotal=item.subtotal
        )
        db.add(cart_item)
    db.commit()

    db.refresh(cart)
    return cart

@router.get("/{cart_id}", response_model=CartResponse)
def get_cart(cart_id: int, db: Session = Depends(get_db)):
    cart = db.query(Cart).filter(Cart.id == cart_id).first()
    if not cart:
        raise HTTPException(status_code=404, detail="Cart not found")
    return cart

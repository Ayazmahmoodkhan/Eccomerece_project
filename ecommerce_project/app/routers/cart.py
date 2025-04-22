# from fastapi import APIRouter, Depends, HTTPException, status
# from sqlalchemy.orm import Session
# from app.database import get_db
# from app.models import Cart, CartItem, Product
# from app.schemas import CartCreate, CartResponse, CartUpdate
# from typing import List

# router = APIRouter(prefix="/carts", tags=["Carts"])

# # Create Cart Endpoint 
# @router.post("/", response_model=CartResponse, status_code=status.HTTP_201_CREATED)
# def create_cart(cart_data: CartCreate, db: Session = Depends(get_db)):

#     grand_total = sum(item.subtotal for item in cart_data.cart_items)

#     # Create the Cart object with the grand_total
#     cart = Cart(
#         user_id=cart_data.user_id,
#         total_amount=cart_data.total_amount,
#         grand_total=grand_total 
#     )

#     db.add(cart)
#     db.commit()
#     db.refresh(cart)

#     # Loop through the cart items and create CartItem records
#     for item in cart_data.cart_items:
#         product = db.query(Product).filter(Product.id == item.product_id).first()
#         if not product:
#             raise HTTPException(status_code=404, detail=f"Product ID {item.product_id} not found.")

#         cart_item = CartItem(
#             cart_id=cart.id,
#             product_id=item.product_id,
#             quantity=item.quantity,
#             subtotal=item.subtotal
#         )
#         db.add(cart_item)

#     db.commit()
#     db.refresh(cart)

#     return cart

# # Get Cart Endpoint
# @router.get("/{cart_id}", response_model=CartResponse)
# def get_cart(cart_id: int, db: Session = Depends(get_db)):
#     cart = db.query(Cart).filter(Cart.id == cart_id).first()
#     if not cart:
#         raise HTTPException(status_code=404, detail="Cart not found")
#     return cart

# # Update Cart Endpoint
# @router.put("/{cart_id}", response_model=CartResponse)
# def update_cart(cart_id: int, cart_data: CartUpdate, db: Session = Depends(get_db)):
#     cart = db.query(Cart).filter(Cart.id == cart_id).first()
#     if not cart:
#         raise HTTPException(status_code=404, detail="Cart not found")

#     # Update the cart's total amount and other properties
#     cart.total_amount = cart_data.total_amount

#     # If cart_items are provided, update them
#     if cart_data.cart_items:
#         # Remove existing cart items
#         db.query(CartItem).filter(CartItem.cart_id == cart.id).delete()

#         # Add updated cart items
#         for item in cart_data.cart_items:
#             product = db.query(Product).filter(Product.id == item.product_id).first()
#             if not product:
#                 raise HTTPException(status_code=404, detail=f"Product ID {item.product_id} not found.")

#             cart_item = CartItem(
#                 cart_id=cart.id,
#                 product_id=item.product_id,
#                 quantity=item.quantity,
#                 subtotal=item.subtotal
#             )
#             db.add(cart_item)

#     db.commit()
#     db.refresh(cart)

#     # Recalculate grand_total if needed
#     grand_total = sum(item.subtotal for item in cart_data.cart_items) if cart_data.cart_items else cart.grand_total
#     cart.grand_total = grand_total

#     db.commit()
#     db.refresh(cart)

#     return cart

# # Delete Cart Endpoint
# @router.delete("/{cart_id}", status_code=status.HTTP_204_NO_CONTENT)
# def delete_cart(cart_id: int, db: Session = Depends(get_db)):
#     cart = db.query(Cart).filter(Cart.id == cart_id).first()
#     if not cart:
#         raise HTTPException(status_code=404, detail="Cart not found")

#     # Delete associated cart items first
#     db.query(CartItem).filter(CartItem.cart_id == cart_id).delete()

#     # Now delete the cart itself
#     db.delete(cart)
#     db.commit()

#     return {"detail": "Cart deleted successfully"}

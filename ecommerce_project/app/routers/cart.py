# from fastapi import APIRouter, Depends, HTTPException, status
# from sqlalchemy.orm import Session
# from typing import List
# from app.database import get_db
# from app.models import Cart, CartItem, Product, User
# from app.schemas import CartCreate, CartResponse, CartUpdate
# from app.auth import get_current_user 

# router = APIRouter(prefix="/carts", tags=["Carts"])

# # Create Cart 
# @router.post("/", response_model=CartResponse, status_code=status.HTTP_201_CREATED)
# def create_cart(
#     cart_data: CartCreate,
#     db: Session = Depends(get_db),
#     current_user: User = Depends(get_current_user)
# ):
#     total_amount = 0.0
#     cart_items = []

#     for item in cart_data.cart_items:
#         product = db.query(Product).filter(Product.id == item.product_id).first()
#         if not product:
#             raise HTTPException(status_code=404, detail=f"Product ID {item.product_id} not found.")

#         subtotal = product.price * item.quantity
#         total_amount += subtotal

#         cart_items.append({
#             "product_id": item.product_id,
#             "quantity": item.quantity,
#             "subtotal": subtotal
#         })

#     cart = Cart(
#         user_id=current_user.id,
#         total_amount=total_amount,
#         grand_total=total_amount
#     )
#     db.add(cart)
#     db.commit()
#     db.refresh(cart)

#     for item in cart_items:
#         cart_item = CartItem(
#             cart_id=cart.id,
#             product_id=item["product_id"],
#             quantity=item["quantity"],
#             subtotal=item["subtotal"]
#         )
#         db.add(cart_item)

#     db.commit()
#     db.refresh(cart)
#     return cart


# # Get Cart 
# @router.get("/{cart_id}", response_model=CartResponse)
# def get_cart(
#     cart_id: int,
#     db: Session = Depends(get_db),
#     current_user: User = Depends(get_current_user)
# ):
#     cart = db.query(Cart).filter(Cart.id == cart_id, Cart.user_id == current_user.id).first()
#     if not cart:
#         raise HTTPException(status_code=404, detail="Cart not found or access denied.")
#     return cart

# # update cart
# @router.put("/{cart_id}", response_model=CartResponse)
# def update_cart(
#     cart_id: int,
#     cart_data: CartUpdate,
#     db: Session = Depends(get_db),
#     current_user: User = Depends(get_current_user)
# ):
#     cart = db.query(Cart).filter(Cart.id == cart_id, Cart.user_id == current_user.id).first()
#     if not cart:
#         raise HTTPException(status_code=404, detail="Cart not found or access denied.")

#     total_amount = 0.0

#     if cart_data.cart_items:
#         db.query(CartItem).filter(CartItem.cart_id == cart.id).delete()

#         for item in cart_data.cart_items:
#             product = db.query(Product).filter(Product.id == item.product_id).first()
#             if not product:
#                 raise HTTPException(status_code=404, detail=f"Product ID {item.product_id} not found.")

#             subtotal = product.price * item.quantity
#             total_amount += subtotal

#             cart_item = CartItem(
#                 cart_id=cart.id,
#                 product_id=item.product_id,
#                 quantity=item.quantity,
#                 subtotal=subtotal
#             )
#             db.add(cart_item)

#     cart.total_amount = total_amount
#     cart.grand_total = total_amount

#     db.commit()
#     db.refresh(cart)
#     return cart

# # cart delete
# @router.delete("/{cart_id}", status_code=status.HTTP_204_NO_CONTENT)
# def delete_cart(
#     cart_id: int,
#     db: Session = Depends(get_db),
#     current_user: User = Depends(get_current_user)
# ):
#     cart = db.query(Cart).filter(Cart.id == cart_id, Cart.user_id == current_user.id).first()
#     if not cart:
#         raise HTTPException(status_code=404, detail="Cart not found or access denied.")

#     db.query(CartItem).filter(CartItem.cart_id == cart.id).delete()
#     db.delete(cart)
#     db.commit()
#     return {"detail": "Cart deleted successfully"}

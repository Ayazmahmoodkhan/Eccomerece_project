from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.models import UserProfile, Address, User, Product
from app.schemas import  ProductCreate, ProductUpdate, ProductResponse
from app.database import get_db
from app.auth import get_current_user
from app.routers.admin import admin_required
from typing import Optional, List
from uuid import uuid4
router = APIRouter()
router=APIRouter(prefix="/product", tags=["Product panel"])
#Product Management
@router.get("/products", response_model=List[ProductResponse])
def get_product(category_id:Optional[int]=None,db: Session=Depends(get_db)):
    if category_id:
        products=db.query(Product).filter(Product.category_id==category_id).all()
    else:
        products=db.query(Product).all()
    if not products:
        raise HTTPException(status_code=404, detail="No products found.")
    return products
    

@router.post("/products")
def add_product(
    product: ProductCreate, admin: User = Depends(admin_required), db: Session = Depends(get_db)):
    product_data = product.dict()
    product_data["admin_id"] = admin.id  
    new_product = Product(**product_data, sku=str(uuid4()))
    db.add(new_product)
    db.commit()
    db.refresh(new_product)
    return {"msg": "Product added successfully", "product": new_product}

@router.put("/products/{product_id}")
def update_product(product_id: int, product: ProductUpdate, admin: User = Depends(admin_required), db: Session = Depends(get_db)):
    existing_product = db.query(Product).filter(Product.id == product_id).first()
    if not existing_product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    for key, value in product.dict(exclude_unset=True).items():
        setattr(existing_product, key, value)
    
    db.commit()
    db.refresh(existing_product)
    return {"msg": "Product updated successfully", "product": existing_product}

@router.delete("/products/{product_id}")
def delete_product(product_id: int, admin: User = Depends(admin_required), db: Session = Depends(get_db)):
    existing_product = db.query(Product).filter(Product.id == product_id).first()
    if not existing_product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    db.delete(existing_product)
    db.commit()
    return {"msg": "Product deleted successfully"}

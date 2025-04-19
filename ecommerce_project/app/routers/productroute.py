from fastapi import APIRouter, Depends, HTTPException, status, Form, UploadFile, File
from sqlalchemy.orm import Session
from app.models import User, Product, ProductImage
from app.schemas import  ProductCreate,ProductResponse
from app.database import get_db
from app.auth import get_current_user
from app.routers.admin import admin_required
from typing import Optional, List
from uuid import uuid4
import os, uuid

router=APIRouter(prefix="/product", tags=["Product panel"])
#Product Management
# @router.get("/products", response_model=List[ProductResponse])
# def get_product(category_id:Optional[int]=None,db: Session=Depends(get_db)):
#     if category_id:
#         products=db.query(Product).filter(Product.category_id==category_id).all()
#     else:
#         products=db.query(Product).all()
#     if not products:
#         raise HTTPException(status_code=404, detail="No products found.")
#     return products
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/products", response_model=ProductResponse)
async def add_product(
    product_name: str = Form(...),
    price: float = Form(...),
    discount: float = Form(...),
    stock: int = Form(...),
    brand: str = Form(...),
    category_id: int = Form(...),
    description: str = Form(...),
    color: str = Form(...),
    shipping_time: str = Form(...),
    images: List[UploadFile] = File(...),
    admin: dict = Depends(admin_required),
    db: Session = Depends(get_db)
):
    # Ensure only admins can add products
    if admin.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can add products")

    # Function to clean double quotes from strings
    def clean_text(value: str) -> str:
        return value.strip('"') if isinstance(value, str) else value

    # Apply clean_text() to remove extra double quotes
    product_name = clean_text(product_name)
    brand = clean_text(brand)
    description = clean_text(description)
    color = clean_text(color)
    shipping_time = clean_text(shipping_time)

    # Create product
    new_product = Product(
        sku=str(uuid.uuid4()),
        product_name=product_name,
        price=price,
        discount=discount,
        stock=stock,
        brand=brand,
        category_id=category_id,
        description=description,
        color=color,
        shipping_time=shipping_time,
        admin_id=admin.id,
    )
    db.add(new_product)
    db.commit()
    db.refresh(new_product)

    image_urls = []  # List to store image URLs

    # Save images
    for image in images:
        filename = f"{uuid.uuid4()}_{image.filename}"
        file_path = os.path.join(UPLOAD_DIR, filename)

        with open(file_path, "wb") as buffer:
            buffer.write(await image.read())

        # Save image URL in ProductImage table
        image_url = f"/static/{filename}"
        product_image = ProductImage(product_id=new_product.id, image_url=image_url)
        db.add(product_image)
        image_urls.append(image_url)  # Append image URL to list

    db.commit()

    # **Return response**
    return ProductResponse(
        id=new_product.id,
        sku=new_product.sku,
        product_name=new_product.product_name,
        price=new_product.price,
        discount=new_product.discount,
        stock=new_product.stock,
        brand=new_product.brand,
        category_id=new_product.category_id,
        description=new_product.description,
        color=new_product.color,
        shipping_time=new_product.shipping_time,
        admin_id=new_product.admin_id,
        images=image_urls,  # Returning image URLs instead of ProductImage objects
    )


@router.get("/products", response_model=List[ProductResponse])
def get_products(
    db: Session = Depends(get_db),
    category_id: Optional[int] = None
):
    query = db.query(Product)
    
    # Filter by category if provided
    if category_id is not None:
        query = query.filter(Product.category_id == category_id)
    products = query.all()
    # If category is selected but no products are found, raise exception
    if category_id is not None and not products:
        raise HTTPException(status_code=404, detail=f"No products found for category ID {category_id}.")
    product_responses = []
    for product in products:
        image_urls = [img.image_url for img in product.images]  # Extract image URLs
        product_dict = product.__dict__.copy()  # Copy dictionary to avoid modifying the original
        product_dict.pop("images", None)  # Remove 'images' key if exists
        product_responses.append(ProductResponse(**product_dict, images=image_urls))
    return product_responses


@router.get("/products/{product_id}", response_model=ProductResponse)
def get_product(product_id: int, db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    image_urls = [img.image_url for img in product.images]  # Extract image URLs
    product_dict = product.__dict__.copy()  # Copy dictionary
    product_dict.pop("images", None)  # Remove 'images' key

    return ProductResponse(**product_dict, images=image_urls)

#update the product
@router.put("/products/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: int,
    product_name: str = Form(None),
    price: float = Form(None),
    discount: float = Form(None),
    stock: int = Form(None),
    brand: str = Form(None),
    category_id: int = Form(None),
    description: str = Form(None),
    color: str = Form(None),
    shipping_time: str = Form(None),
    images: List[UploadFile] = File(None),
    db: Session = Depends(get_db),
    admin: dict = Depends(admin_required)
):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    if admin.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can update products")
    update_fields = {
        "product_name": product_name,
        "price": price,
        "discount": discount,
        "stock": stock,
        "brand": brand,
        "category_id": category_id,
        "description": description,
        "color": color,
        "shipping_time": shipping_time,
    }
    for key, value in update_fields.items():
        if value is not None:  # Sirf provided fields update karni hain
            setattr(product, key, value)

    db.commit()
    db.refresh(product)


    image_urls = [img.image_url for img in product.images]  # Default: Purani images rahengi
    if images:  # Agar naye images upload hoon
        db.query(ProductImage).filter(ProductImage.product_id == product.id).delete()
        db.commit()
        
        image_urls = []  
        for image in images:
            filename = f"{uuid.uuid4()}_{image.filename}"
            file_path = os.path.join(UPLOAD_DIR, filename)

            with open(file_path, "wb") as buffer:
                buffer.write(await image.read())

            image_url = f"/static/{filename}"
            db.add(ProductImage(product_id=product.id, image_url=image_url))
            image_urls.append(image_url)  

        db.commit()


    return ProductResponse(
        id=product.id,
        sku=product.sku,
        product_name=product.product_name,
        price=product.price,
        discount=product.discount,
        stock=product.stock,
        brand=product.brand,
        category_id=product.category_id,
        description=product.description,
        color=product.color,
        shipping_time=product.shipping_time,
        images=image_urls 
    )

#product update end

@router.delete("/products/{product_id}")
def delete_product(product_id: int, db: Session = Depends(get_db), admin: dict = Depends(admin_required)):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    if admin.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can delete products")

    db.query(ProductImage).filter(ProductImage.product_id == product.id).delete()

    db.delete(product)
    db.commit()
    
    return {"message": "Product deleted successfully"}

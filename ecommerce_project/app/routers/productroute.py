from fastapi import APIRouter, Depends, HTTPException, status, Form, UploadFile, File, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, cast, Float
from app.models import User, Product, ProductImage, Category,ProductVariant,VariantAttribute,CategoryVariantAttribute,Review
from app.schemas import  ProductCreate,ProductResponse, ProductVariantCreate,ProductVariantResponse
from app.database import get_db
from app.auth import get_current_user
from app.routers.admin import admin_required
from typing import Optional, List
from uuid import uuid4
import os, uuid, json

router=APIRouter(prefix="/products", tags=["Product panel"])
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
UPLOAD_DIR = "media/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/", response_model=ProductResponse)
async def add_product(
    product_name: str = Form(...),
    brand: str = Form(...),
    category_id: int = Form(...),
    description: str = Form(...),
    variants: List[str] = Form(...), 
    variant_images: List[UploadFile] = File(...),
    admin: dict = Depends(admin_required),
    db: Session = Depends(get_db)
):
    # ----- Admin check -----
    if admin.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can add products")

    # ----- Category check -----
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(status_code=400, detail=f"Category ID {category_id} does not exist")

    # ----- Clean text -----
    def clean(val: str) -> str:
        return val.strip('"') if isinstance(val, str) else val

    product_name = clean(product_name)
    brand = clean(brand)
    description = clean(description)

    # ----- Create product -----
    new_product = Product(
        sku=str(uuid.uuid4()),
        product_name=product_name,
        brand=brand,
        category_id=category_id,
        description=description,
        admin_id=admin.id
    )
    db.add(new_product)
    db.commit()
    db.refresh(new_product)

    # ----- Handle variants -----
    image_index = 0
    created_variants = []

    for idx, variant_str in enumerate(variants):
        try:
            variant_data = json.loads(variant_str)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail=f"Variant at index {idx} has invalid JSON format.")

        # Validate required fields
        required_fields = ["price", "stock"]
        for field in required_fields:
            if field not in variant_data:
                raise HTTPException(status_code=400, detail=f"'{field}' is required in variant at index {idx}")

        # Extract fields
       
        attributes = variant_data.get("attributes", {})
        price = variant_data["price"]
        stock = variant_data["stock"]
        discount = variant_data.get("discount", 0)
        shipping_time = variant_data.get("shipping_time")
        image_count = variant_data.get("image_count", 1)

        # ----- Field validations -----
        if not isinstance(price, (int, float)) or price < 0:
            raise HTTPException(status_code=400, detail=f"Invalid 'price' in variant at index {idx}")

        if not isinstance(stock, int) or stock < 0:
            raise HTTPException(status_code=400, detail=f"Invalid 'stock' in variant at index {idx}")

        if not isinstance(discount, int) or not (0 <= discount <= 100):
            raise HTTPException(status_code=400, detail=f"'discount' must be between 0 and 100 at index {idx}")

        if shipping_time is not None and (not isinstance(shipping_time, int) or shipping_time < 0):
            raise HTTPException(status_code=400, detail=f"Invalid 'shipping_time' in variant at index {idx}")

        if not isinstance(attributes, dict):
            raise HTTPException(status_code=400, detail=f"'attributes' must be a dictionary in variant at index {idx}")

        if not isinstance(image_count, int) or image_count < 1:
            raise HTTPException(status_code=400, detail=f"Invalid 'image_count' in variant at index {idx}")

        # ----- Save Variant -----
        direct_fields = {"price", "stock", "discount", "shipping_time", "image_count"}

        # Now extract all keys except those and use as attributes
        attributes = {k: v for k, v in variant_data.items() if k not in direct_fields}
        new_variant = ProductVariant(
            product_id=new_product.id,
            price=price,
            stock=stock,
            discount=discount,
            shipping_time=shipping_time,
            attributes=attributes
        )
        db.add(new_variant)
        db.commit()
        db.refresh(new_variant)

        # ----- Save Images -----
        variant_image_urls = []
        for _ in range(image_count):
            if image_index >= len(variant_images):
                raise HTTPException(status_code=400, detail=f"Not enough images provided for variant at index {idx}")

            image = variant_images[image_index]
            safe_filename = image.filename.replace(" ", "_")
            filename = f"{uuid.uuid4()}_{safe_filename}"
            file_path = os.path.join(UPLOAD_DIR, filename)

            # Save image
            with open(file_path, "wb") as buffer:
                buffer.write(await image.read())

            image_url = f"/media/uploads/{filename}"
            db.add(ProductImage(variant_id=new_variant.id, image_url=image_url))
            variant_image_urls.append(image_url)
            image_index += 1

        # ----- Build variant response -----
        created_variants.append({
            "id": new_variant.id,
            "price": price,
            "stock": stock,
            "discount": discount,
            "shipping_time": shipping_time,
            "created_at": new_variant.created_at,
            "updated_at": new_variant.updated_at,
            "attributes": attributes,
            "images": variant_image_urls
        })

    db.commit()

    # ----- Return response -----
    return ProductResponse(
        id=new_product.id,
        sku=new_product.sku,
        product_name=new_product.product_name,
        brand=new_product.brand,
        category_id=new_product.category_id,
        description=new_product.description,
        admin_id=new_product.admin_id,
        created_at=new_product.created_at,
        updated_at=new_product.updated_at,
        variants=created_variants,
        images=[]
    )




#get all products
@router.get("/allproducts", response_model=List[ProductResponse])
def get_products(db: Session = Depends(get_db)):
    products = db.query(Product).all()

    product_responses = []
    for product in products:
        variants = []
        for variant in product.variants:
            variant_dict = {
                "id": variant.id,
                "price": variant.price,
                "stock": variant.stock,
                "discount": variant.discount,
                "shipping_time": variant.shipping_time,
                "attributes": variant.attributes or {}, # fallback to empty dict if None
                "images": [img.image_url for img in variant.images],
            }
            variants.append(ProductVariantResponse(**variant_dict))

        product_dict = {
            "id": product.id,
            "sku": product.sku,
            "admin_id": product.admin_id,
            "product_name": product.product_name,
            "brand": product.brand,
            "category_id": product.category_id,
            "description": product.description,
            "created_at": product.created_at,
            "updated_at": product.updated_at,
            "variants": variants,
        }
        product_responses.append(ProductResponse(**product_dict))

    return product_responses

# GET product by ID
from fastapi import Path
from typing_extensions import Annotated
@router.get("/{product_id}", response_model=ProductResponse)
def get_product(product_id: Annotated[int, Path(ge=1)], db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    variants = db.query(ProductVariant).filter_by(product_id=product.id).all()
    variant_list = []
    for variant in variants:
        images = db.query(ProductImage).filter_by(variant_id=variant.id).all()
        image_urls = [img.image_url for img in images]
        variant_list.append({
            "id": variant.id,
            "price": variant.price,
            "stock": variant.stock,
            "discount": variant.discount,
            "shipping_time": variant.shipping_time,
            "attributes": variant.attributes,
            "images": image_urls
        })

    return ProductResponse(
        id=product.id,
        sku=product.sku,
        product_name=product.product_name,
        brand=product.brand,
        category_id=product.category_id,
        description=product.description,
        admin_id=product.admin_id,
        created_at=product.created_at,
        updated_at=product.updated_at,
        variants=variant_list,
        images=[]
    )

#get product by category
@router.get("/category/{category_id}", response_model=List[ProductResponse])
def get_products_by_category(category_id: Annotated[int, Path(ge=1)], db: Session = Depends(get_db)):
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(
            status_code=404,
            detail=f"Category with ID {category_id} does not exist."
        )
    products = db.query(Product).filter(Product.category_id == category_id).all()
    response = []
    for product in products:
        variants = db.query(ProductVariant).filter_by(product_id=product.id).all()
        variant_list = []
        for variant in variants:
            images = db.query(ProductImage).filter_by(variant_id=variant.id).all()
            image_urls = [img.image_url for img in images]
            variant_list.append({
                "id": variant.id,
                "price": variant.price,
                "stock": variant.stock,
                "discount": variant.discount,
                "shipping_time": variant.shipping_time,
                "attributes": variant.attributes,
                "images": image_urls
            })

        response.append(ProductResponse(
            id=product.id,
            sku=product.sku,
            product_name=product.product_name,
            brand=product.brand,
            category_id=product.category_id,
            description=product.description,
            admin_id=product.admin_id,
            created_at=product.created_at,
            updated_at=product.updated_at,
            variants=variant_list,
            images=[]
        ))

    return response

# Filter Products by Rating

from app.models import Product, Review

@router.get("/rating/by-rating", response_model=List[ProductResponse])
def get_products_by_rating(
    min_rating: Optional[float] = Query(0, ge=0, le=5),
    db: Session = Depends(get_db)
):
    subquery = (
        db.query(
            Review.product_id,
            func.avg(Review.rating).label("avg_rating")
        )
        .group_by(Review.product_id)
        .subquery()
    )

    products = (
        db.query(Product)
        .join(subquery, Product.id == subquery.c.product_id)
        .filter(subquery.c.avg_rating >= min_rating)
        .all()
    )

    product_responses = []
    for product in products:
        variants = db.query(ProductVariant).filter_by(product_id=product.id).all()
        variant_list = []

        for variant in variants:
            images = db.query(ProductImage).filter_by(variant_id=variant.id).all()
            image_urls = [img.image_url for img in images]
            variant_list.append(ProductVariantResponse(
                id=variant.id,
                price=variant.price,
                stock=variant.stock,
                discount=variant.discount,
                shipping_time=variant.shipping_time,
                attributes=variant.attributes,
                images=image_urls
            ))

        product_responses.append(ProductResponse(
            id=product.id,
            sku=product.sku,
            product_name=product.product_name,
            brand=product.brand,
            category_id=product.category_id,
            description=product.description,
            admin_id=product.admin_id,
            created_at=product.created_at,
            updated_at=product.updated_at,
            variants=variant_list,
            images=[]
        ))

    return product_responses

from fastapi import APIRouter, Depends, HTTPException, status, Form, UploadFile, File
from sqlalchemy.orm import Session
from app.models import User, Product, ProductImage, Category,ProductVariant,VariantAttribute,CategoryVariantAttribute,Review
from app.schemas import  ProductCreate,ProductResponse, ProductVariantCreate
from app.database import get_db
from app.auth import get_current_user
from app.routers.admin import admin_required
from typing import Optional, List
from uuid import uuid4
import os, uuid, json

router=APIRouter(prefix="/product", tags=["Product panel"])
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/products", response_model=ProductResponse)
async def add_product(
    product_name: str = Form(...),
    brand: str = Form(...),
    category_id: int = Form(...),
    description: str = Form(...),
    variants: List[str] = Form(...),  # JSON string with attributes
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
            filename = f"{uuid.uuid4()}_{image.filename}"
            file_path = os.path.join(UPLOAD_DIR, filename)

            # Save image
            with open(file_path, "wb") as buffer:
                buffer.write(await image.read())

            image_url = f"/static/uploads/{filename}"
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




@router.get("/products", response_model=List[ProductResponse])
def get_products(
    db: Session = Depends(get_db),
    category_id: Optional[int] = None
):
    query = db.query(Product)

    # Check if category_id exists in the database
    if category_id is not None:
        category_exists = db.query(Category).filter(Category.id == category_id).first()
        if not category_exists:
            raise HTTPException(status_code=400, detail=f"Invalid category ID: {category_id}")
        query = query.filter(Product.category_id == category_id)

    products = query.all()

    if category_id is not None and not products:
        raise HTTPException(status_code=404, detail=f"No products found for category ID {category_id}.")

    product_responses = []
    for product in products:
        image_urls = [img.image_url for img in product.images]  # Extract image URLs
        product_dict = product.__dict__.copy()  # Copy dictionary to avoid modifying the original
        product_dict.pop("images", None)  # Remove 'images' key if exists
        product_responses.append(ProductResponse(**product_dict, images=image_urls))

    return product_responses
# GET product by ID
from fastapi import Path
from typing_extensions import Annotated
@router.get("/products/{product_id}", response_model=ProductResponse)
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
            "created_at": variant.created_at,
            "updated_at": variant.updated_at,
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
@router.get("/products/category/{category_id}", response_model=List[ProductResponse])
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
                "created_at": variant.created_at,
                "updated_at": variant.updated_at,
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


@router.delete("/products/{product_id}")
def delete_product(product_id: int, db: Session = Depends(get_db), admin: dict = Depends(admin_required)):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    # Step 1: Delete related reviews
    db.query(Review).filter_by(product_id=product_id).delete(synchronize_session=False)
    db.query(ProductImage).filter(ProductImage.variant_id.in_(
        db.query(ProductVariant.id).filter_by(product_id=product_id))).delete(synchronize_session=False)
    db.query(ProductVariant).filter_by(product_id=product_id).delete()
    db.delete(product)
    db.commit()
    return {"detail": "Product deleted successfully"}

@router.put("/products/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: int,
    product_name: Optional[str] = Form(None),
    brand: Optional[str] = Form(None),
    category_id: Optional[int] = Form(None),
    description: Optional[str] = Form(None),
    variants: Optional[List[str]] = Form(None),
    variant_images: Optional[List[UploadFile]] = File(None),
    admin: dict = Depends(admin_required),
    db: Session = Depends(get_db)
):
    # Check if product exists
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Update basic product fields if provided
    if product_name:
        if not isinstance(product_name, str) or len(product_name.strip()) == 0:
            raise HTTPException(status_code=400, detail="Invalid product name")
        product.product_name = product_name.strip('"')

    if brand:
        if not isinstance(brand, str) or len(brand.strip()) == 0:
            raise HTTPException(status_code=400, detail="Invalid brand")
        product.brand = brand.strip('"')

    if description:
        if not isinstance(description, str) or len(description.strip()) == 0:
            raise HTTPException(status_code=400, detail="Invalid description")
        product.description = description.strip('"')

    if category_id:
        category = db.query(Category).filter(Category.id == category_id).first()
        if not category:
            raise HTTPException(status_code=400, detail="Category not found")
        product.category_id = category_id

    db.commit()
    db.refresh(product)

    created_variants = []
    image_index = 0

    if variants:
        # Remove old variants and images
        db.query(ProductImage).filter(ProductImage.variant_id.in_(
            db.query(ProductVariant.id).filter_by(product_id=product_id)
        )).delete(synchronize_session=False)

        db.query(ProductVariant).filter_by(product_id=product_id).delete()

        for idx, variant_str in enumerate(variants):
            try:
                variant_data = json.loads(variant_str)
            except json.JSONDecodeError:
                raise HTTPException(status_code=400, detail=f"Variant at index {idx} has invalid JSON format.")

            # Validate variant data using ProductVariantCreate model
            try:
                variant = ProductVariantCreate(**variant_data)
            except ValueError as e:
                raise HTTPException(status_code=400, detail=f"Invalid data for variant at index {idx}: {e}")

            attributes = {k: v for k, v in variant_data.items() if k not in {"price", "stock", "discount", "shipping_time", "image_count"}}
            new_variant = ProductVariant(
                product_id=product.id,
                price=variant.price,
                stock=variant.stock,
                discount=variant.discount,
                shipping_time=variant.shipping_time,
                attributes=attributes
            )
            db.add(new_variant)
            db.commit()
            db.refresh(new_variant)

            image_count = variant.image_count
            image_urls = []
            for _ in range(image_count):
                if variant_images and image_index < len(variant_images):
                    image = variant_images[image_index]
                    filename = f"{uuid.uuid4()}_{image.filename}"
                    file_path = os.path.join(UPLOAD_DIR, filename)
                    with open(file_path, "wb") as buffer:
                        buffer.write(await image.read())
                    image_url = f"/static/uploads/{filename}"
                    db.add(ProductImage(variant_id=new_variant.id, image_url=image_url))
                    image_urls.append(image_url)
                    image_index += 1

            created_variants.append({
                "id": new_variant.id,
                "price": new_variant.price,
                "stock": new_variant.stock,
                "discount": new_variant.discount,
                "shipping_time": new_variant.shipping_time,
                "created_at": new_variant.created_at,
                "updated_at": new_variant.updated_at,
                "attributes": new_variant.attributes,
                "images": image_urls
            })

    db.commit()

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
        variants=created_variants if variants else [],
        images=[]
    )

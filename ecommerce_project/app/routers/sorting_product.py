from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, asc, cast, Float
from typing import List, Optional
from app.database import get_db
from app.models import Product, ProductVariant, OrderItem, Review
from app.schemas import ProductResponse
from enum import Enum
router = APIRouter(prefix="/sort")

class SortOrderEnum(str, Enum):
    asc = "asc"
    desc = "desc"

@router.get("/sort_by_price/", response_model=List[ProductResponse])
def sort_products_by_price(
    sort_order: Optional[SortOrderEnum] = Query(default=None),
    db: Session = Depends(get_db)
):
    """
    Endpoint to sort products by price.
    - No sort_order => Random/mixed order.
    - 'asc' => Sort price low to high.
    - 'desc' => Sort price high to low.
    """

    query = db.query(Product).join(Product.variants)

    if sort_order == SortOrderEnum.asc:
        query = query.order_by(asc(ProductVariant.price))
    elif sort_order == SortOrderEnum.desc:
        query = query.order_by(desc(ProductVariant.price))
    # else: leave as is for random/mixed order

    products = query.all()

    if not products:
        raise HTTPException(status_code=404, detail="No products found.")

    return products
from sqlalchemy import func, desc
from typing import Optional
from fastapi import Query
class SortByEnum(str, Enum):
    popularity = "popularity"
    rating = "rating"
@router.get("/popu_or_rating/")
def sort_products(
    sort_by: Optional[SortByEnum] = Query(default=None),
    db: Session = Depends(get_db)
):
    query = db.query(Product)

    if sort_by == SortByEnum.popularity:
        query = (
            query
            .join(Product.variants)
            .join(OrderItem, OrderItem.variant_id == ProductVariant.id)
            .group_by(Product.id)
            .order_by(desc(func.count(OrderItem.id)))
        )

    elif sort_by == SortByEnum.rating:
        query = (
            query
            .outerjoin(Review, Review.product_id == Product.id)
            .group_by(Product.id)
            .order_by(desc(func.avg(Review.rating)))  # No need to cast anymore
        )

    products = query.all()
    return products

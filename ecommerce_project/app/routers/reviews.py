from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app import models, schemas
from app.database import get_db
from app.auth import get_current_user
from app.models import User

router = APIRouter(prefix="/reviews", tags=["Reviews"])

# Create a Review 
@router.post("/", response_model=schemas.ReviewResponse, status_code=status.HTTP_201_CREATED)
def create_review(
    review: schemas.ReviewCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):  

    if review.rating < 1 or review.rating > 5:
        raise HTTPException(
            status_code=400,
            detail="Rating must be between 1 and 5"
        )
    purchased = db.query(models.OrderItem).join(models.Order).filter(
        models.Order.user_id == current_user.id,
        models.OrderItem.product_id == review.product_id
    ).first()

    if not purchased:
        raise HTTPException(
            status_code=403,
            detail="You can only review products you have purchased."
        )

    existing_review = db.query(models.Review).filter(
        models.Review.user_id == current_user.id,
        models.Review.product_id == review.product_id
    ).first()

    if existing_review:
        raise HTTPException(
            status_code=400,
            detail="You have already reviewed this product."
        )

    new_review = models.Review(
        product_id=review.product_id,
        rating=review.rating,
        description=review.description,
        user_id=current_user.id,
        email = review.email
    )

    review_email = review.email if review.email else current_user.email

    db.add(new_review)
    db.commit()
    db.refresh(new_review)

    return schemas.ReviewResponse(
        id=new_review.id,
        product_id=new_review.product_id,
        user_id=new_review.user_id,
        email=review_email,
        rating=new_review.rating,
        description=new_review.description,
        created_at=new_review.created_at
    )


# Get all reviews
@router.get("/", response_model=List[schemas.ReviewResponse])
def get_all_reviews(db: Session = Depends(get_db)):
    return db.query(models.Review).all()

# Get a single review by ID
@router.get("/{review_id}", response_model=schemas.ReviewResponse)
def get_review(review_id: int, db: Session = Depends(get_db)):
    review = db.query(models.Review).filter(models.Review.id == review_id).first()
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    return review

# Delete a review
@router.delete("/{review_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_review(
    review_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    review = db.query(models.Review).filter(
        models.Review.id == review_id,
        models.Review.user_id == current_user.id
    ).first()

    if not review:
        raise HTTPException(status_code=404, detail="Review not found or not yours")

    db.delete(review)
    db.commit()
    return {"detail": "Review deleted successfully"}

# Get reviews for a product by product_id
@router.get("/product_id/{product_id}", response_model=List[schemas.ReviewResponse])
def get_reviews_by_product(
    product_id: int, 
    db: Session = Depends(get_db)
):
    reviews = db.query(models.Review).filter(models.Review.product_id == product_id).all()
    if not reviews:
        raise HTTPException(status_code=404, detail="No reviews found for this product")
    
    return reviews

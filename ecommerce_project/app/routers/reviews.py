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
    # Check if the user has already reviewed the product
    existing_review = db.query(models.Review).filter(
        models.Review.user_id == current_user.id,
        models.Review.product_id == review.product_id
    ).first()

    if existing_review:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You have already reviewed this product."
        )

    new_review = models.Review(
        product_id=review.product_id,
        rating=review.rating,
        description=review.description,
        user_id=current_user.id
    )
    db.add(new_review)
    db.commit()
    db.refresh(new_review)
    return new_review

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


@router.get("/product_id/{product_id}", response_model=List[schemas.ReviewResponse])
def get_reviews_by_product(
    product_id: int, 
    db: Session = Depends(get_db)
):
    reviews = db.query(models.Review).filter(models.Review.product_id == product_id).all()
    if not reviews:
        raise HTTPException(status_code=404, detail="No reviews found for this product")
    
    return reviews

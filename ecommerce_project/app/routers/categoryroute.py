from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.auth import get_current_user
from app.utils import pwd_context
from app.database import get_db
from app.models import Category
from typing import List
from app.schemas import  CategoryResponse, CategoryCreate,CategoryUpdate
router=APIRouter()
router = APIRouter(prefix="/category", tags=["Category List"])
# Public: Get all categories 
@router.get("/categories", response_model=list[CategoryResponse])
def get_categories(db: Session = Depends(get_db)):
    categories=db.query(Category).all()
    if not categories:
        raise HTTPException(status_code=404, detail="No category found")
    return categories

# Get categories by ID
@router.get("/{category_id}", response_model=List[CategoryResponse])
def get_categories(
    category_id: int,
    db: Session = Depends(get_db)
):
    categories = db.query(Category).filter(Category.id == category_id).all()
    if not categories:
        raise HTTPException(status_code=404, detail="No category found")
    return categories

# Admin: Create a new category
@router.post("/categories", response_model=CategoryResponse)
def create_category(category: CategoryCreate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
 
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admin can create categories.")
    existing = db.query(Category).filter(Category.category_name == category.category_name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Category with this name already exists.")

    new_category = Category(**category.dict())
    db.add(new_category)
    db.commit()
    db.refresh(new_category)
    return new_category


# Admin: Update category
@router.put("/categories/{category_id}", response_model=CategoryResponse)
def update_category(category_id: int, category_update: CategoryUpdate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admin can update categories.")

    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found.")
    existing = db.query(Category).filter(Category.category_name == category.category_name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Category with this name already exists.")


    for key, value in category_update.dict(exclude_unset=True).items():
        setattr(category, key, value)

    db.commit()
    db.refresh(category)
    return category

# Admin: Delete category
@router.delete("/categories/{category_id}")
def delete_category(category_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admin can delete categories.")

    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found.")

    db.delete(category)
    db.commit()
    return {"message": "Category deleted successfully"}
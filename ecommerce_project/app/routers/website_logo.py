from fastapi import APIRouter, HTTPException, UploadFile, Form, Depends
from fastapi.responses import JSONResponse
from typing import Optional
import shutil
import os
from sqlalchemy.orm import Session
from app import models, schemas
from app.auth import get_current_user
from app.database import get_db
import uuid

router = APIRouter(
    prefix="/admin/pages",
    tags=["Website Pages"]
)

UPLOAD_DIR = "media/website_logo"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.get("/website_logo", response_model=schemas.WebsiteLogoBase)
async def get_website_logo(db: Session = Depends(get_db)):
    website_logo = db.query(models.WebsiteLogo).first()
    if not website_logo:
        raise HTTPException(status_code=404, detail="Website logo not found")
    return website_logo


@router.post("/website_logo", response_model=schemas.WebsiteLogoBase)
async def create_or_update_website_logo(
    name: str = Form(...),
    logo: Optional[UploadFile] = None,
    admin: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if admin.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can perform this action")

    website_logo = db.query(models.WebsiteLogo).first()

    # Handle logo upload and cleanup
    logo_path = None
    if logo:
        
        if website_logo and website_logo.logo_path:
            try:
                os.remove(website_logo.logo_path)
            except FileNotFoundError:
                pass

        filename = f"{uuid.uuid4().hex[:8]}_{logo.filename.replace(' ', '_').lower()}"
        logo_path = os.path.join(UPLOAD_DIR, filename)
        with open(logo_path, "wb") as buffer:
            shutil.copyfileobj(logo.file, buffer)

    if website_logo:
        website_logo.name = name
        if logo_path:
            website_logo.logo_path = logo_path
        db.commit()
        db.refresh(website_logo)
    else:
        website_logo = models.WebsiteLogo(name=name, logo_path=logo_path)
        db.add(website_logo)
        db.commit()
        db.refresh(website_logo)

    return website_logo



# @router.put("/website_logo", response_model=schemas.WebsiteLogoBase)
# async def update_website_logo(
#     name: Optional[str] = Form(None),
#     logo: Optional[UploadFile] = None,
#     admin: dict = Depends(get_current_user),
#     db: Session = Depends(get_db)
# ):
   
#     if admin.role != "admin":
#         raise HTTPException(status_code=403, detail="Only admins can perform this action")

#     website_logo = db.query(models.WebsiteLogo).first()
#     if not website_logo:
#         raise HTTPException(status_code=404, detail="Website logo not found")

#     if name:
#         website_logo.name = name

#     if logo:
#         logo_path = os.path.join(UPLOAD_DIR, logo.filename)
#         with open(logo_path, "wb") as buffer:
#             shutil.copyfileobj(logo.file, buffer)
#         website_logo.logo_path = logo_path

#     db.commit()
#     db.refresh(website_logo)

#     return website_logo


@router.delete("/website_logo")
async def delete_website_logo(
    admin: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
   
    if admin.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can perform this action")

    website_logo = db.query(models.WebsiteLogo).first()
    if not website_logo:
        raise HTTPException(status_code=404, detail="Website logo not found")

    if website_logo.logo_path:
        try:
            os.remove(website_logo.logo_path)
        except FileNotFoundError:
            pass

    db.delete(website_logo)
    db.commit()

    return {"message": "Website logo and name deleted successfully"}

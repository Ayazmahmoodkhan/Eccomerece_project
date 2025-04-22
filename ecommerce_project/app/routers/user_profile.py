from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.orm import Session
import shutil
import os
from app.database import get_db
from app.models import UserProfile

router = APIRouter(prefix="/profiles", tags=["Profiles"])

@router.post("/upload-picture/")
def upload_profile_picture(user_id: int, file: UploadFile = File(...), db: Session = Depends(get_db)):
   
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image.")

    upload_dir = "media/profiles"
    os.makedirs(upload_dir, exist_ok=True)

    file_ext = file.filename.split(".")[-1]
    file_path = f"{upload_dir}/user_{user_id}.{file_ext}"
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)


    profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="User profile not found")

    profile.profile_picture = file_path
    db.commit()

    return {"message": "Profile picture uploaded successfully", "file_path": file_path}

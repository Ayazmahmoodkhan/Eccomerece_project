import jwt
from datetime import timedelta, datetime
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status, Header
from sqlalchemy.orm import Session
from app.models import User
from app.database import get_db

SECRET_KEY = "e5f8a7d9c2b44e5db11a6e3f9f6b7c8d9a4e5f2a1b3c4d5e6f7a8b9c0d1e2f3"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRES_MINUTES = 120


def create_access_token(user_id: int):
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRES_MINUTES)
    payload = {
        "user_id": user_id,
        "exp": expire,  # Expiry time
        "sub": str(user_id)  # Subject field (optional)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: int = payload.get("user_id")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token structure")
        user = db.query(User).filter(User.id == user_id).first()
        if user is None:
            raise HTTPException(status_code=401, detail="Invalid user")
        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

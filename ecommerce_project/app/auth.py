from datetime import timedelta, datetime
import jwt
from fastapi.security import OAuth2PasswordBearer
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from models import User
from database import get_db

SECRET_KEY = "e5f8a7d9c2b44e5db11a6e3f9f6b7c8d9a4e5f2a1b3c4d5e6f7a8b9c0d1e2f3"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRES_MINUTES = 60

def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = {"sub": data.get("sub")} 
    expire = datetime.utcnow() + (expires_delta if expires_delta else timedelta(minutes=ACCESS_TOKEN_EXPIRES_MINUTES))
    
    to_encode.update({"exp": expire})  # Update `to_encode` without overwriting
    
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.token == token).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    return user

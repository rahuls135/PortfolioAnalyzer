from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from sqlalchemy.orm import Session
import os

from database import get_db
import models

security = HTTPBearer()

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
):
    print("Authorization header received:", credentials)
    token = credentials.credentials
    print("RAW TOKEN (first 30 chars):", token[:30])
    print("JWT SECRET PRESENT:", bool(os.getenv("SUPABASE_JWT_SECRET")))

    try:
        payload = jwt.decode(
            token,
            os.getenv("SUPABASE_JWT_SECRET"),
            algorithms=["HS256"],
            options={"verify_aud": False}  # <-- skip audience check for now
        )
        print("payload:", payload)
    except JWTError as e:
        print("JWT decode error:", e)
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    supabase_user_id = payload.get("sub")

    if not supabase_user_id:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    user = db.query(models.User).filter(
        models.User.supabase_user_id == supabase_user_id
    ).first()

    if not user:
        raise HTTPException(status_code=401, detail="User not registered")

    return user

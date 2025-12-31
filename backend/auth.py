from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from sqlalchemy.orm import Session
import os
import requests

from database import get_db
import models

security = HTTPBearer()

SUPABASE_URL = os.getenv("SUPABASE_URL")

if not SUPABASE_URL:
    raise RuntimeError("SUPABASE_URL not set")

JWKS_URL = f"{SUPABASE_URL}/auth/v1/jwks"


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
):
    print("Authorization header:", credentials)

    token = credentials.credentials

    try:
        # Get token header (to read `kid`)
        header = jwt.get_unverified_header(token)
        kid = header.get("kid")
        if not kid:
            raise HTTPException(status_code=401, detail="Invalid token header")

        # Fetch JWKS
        jwks = requests.get(JWKS_URL).json()
        keys = jwks.get("keys", [])

        # Find matching key
        key = next((k for k in keys if k["kid"] == kid), None)
        if not key:
            raise HTTPException(status_code=401, detail="Signing key not found")
        
        print("JWT length:", len(token))
        print("JWT preview:", token[:20])

        # Decode token (RS256)
        payload = jwt.decode(
            token,
            key,
            algorithms=["RS256"],
            options={"verify_aud": False},  # disable audience check for now
        )
        print("JWT payload:", payload)

    except JWTError as e:
        print("JWT decode error:", e)
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    # Extract Supabase user ID
    supabase_user_id = payload.get("sub")
    if not supabase_user_id:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    # Load internal user
    user = (
        db.query(models.User)
        .filter(models.User.supabase_user_id == supabase_user_id)
        .first()
    )

    if not user:
        raise HTTPException(status_code=401, detail="User not registered")

    return user

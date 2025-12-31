from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from jwt import PyJWKClient
import os
from sqlalchemy.orm import Session

from database import get_db
import models

security = HTTPBearer()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_PUB_KEY = os.getenv("SUPABASE_PUB_KEY") # You need this!

# Correct JWKS URL format for Supabase
JWKS_URL = f"{SUPABASE_URL}/auth/v1/.well-known/jwks.json"

# Initialize with headers
jwks_client = PyJWKClient(
    JWKS_URL,
    headers={
        "apikey": SUPABASE_PUB_KEY,
        "Authorization": f"Bearer {SUPABASE_PUB_KEY}"
    }
)

def _decode_supabase_token(token: str) -> str:
    try:
        signing_key = jwks_client.get_signing_key_from_jwt(token)
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["ES256"],
            audience="authenticated",
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")

    supabase_user_id = payload.get("sub")
    if not supabase_user_id:
        raise HTTPException(status_code=401, detail="User ID missing from token")
    return supabase_user_id


def get_supabase_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> str:
    return _decode_supabase_token(credentials.credentials)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
):
    supabase_user_id = _decode_supabase_token(credentials.credentials)

    user = (
        db.query(models.User)
        .filter(models.User.supabase_user_id == supabase_user_id)
        .first()
    )

    if not user:
        raise HTTPException(status_code=401, detail="User not found in local database")

    return user

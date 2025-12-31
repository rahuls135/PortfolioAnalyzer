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
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY") # You need this!

# Correct JWKS URL format for Supabase
JWKS_URL = f"{SUPABASE_URL}/auth/v1/.well-known/jwks.json"

# Initialize with headers
jwks_client = PyJWKClient(
    JWKS_URL,
    headers={
        "apikey": SUPABASE_ANON_KEY,
        "Authorization": f"Bearer {SUPABASE_ANON_KEY}"
    }
)

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
):
    token = credentials.credentials

    try:
        # 1. Get the correct signing key from the JWKS
        signing_key = jwks_client.get_signing_key_from_jwt(token)

        # 2. Decode the payload
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

    # 3. Extract the Supabase UUID (the 'sub' claim)
    supabase_user_id = payload.get("sub")
    if not supabase_user_id:
        raise HTTPException(status_code=401, detail="User ID missing from token")

    # 4. Fetch the actual user from your database
    user = (
        db.query(models.User)
        .filter(models.User.supabase_user_id == supabase_user_id)
        .first()
    )

    if not user:
        # This happens if the user exists in Supabase but hasn't 
        # been synced/created in your local database yet.
        raise HTTPException(status_code=401, detail="User not found in local database")

    return user
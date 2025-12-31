from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from sqlalchemy.orm import Session
import os
from jwt import PyJWKClient
from database import get_db
import models

security = HTTPBearer()

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
):
    token = credentials.credentials
    
    try:
        # Get JWKS URL from Supabase
        supabase_url = os.getenv("SUPABASE_URL")
        jwks_url = f"{supabase_url}/auth/v1/jwks"
        
        # Fetch the signing key
        jwks_client = PyJWKClient(jwks_url)
        signing_key = jwks_client.get_signing_key_from_jwt(token)
        
        # Decode the token
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            audience="authenticated"
        )
        
        print("payload:", payload)
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError as e:
        print("JWT decode error:", e)
        raise HTTPException(status_code=401, detail="Invalid token")
    
    supabase_user_id = payload.get("sub")
    if not supabase_user_id:
        raise HTTPException(status_code=401, detail="Invalid token payload")
    
    user = db.query(models.User).filter(
        models.User.supabase_user_id == supabase_user_id
    ).first()
    
    if not user:
        raise HTTPException(status_code=401, detail="User not registered")
    
    return user
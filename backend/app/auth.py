"""
Auth dependency.

Supabase issues JWTs signed with supabase_jwt_secret.
We verify the token here so every protected route gets a typed CurrentUser.
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from pydantic import BaseModel
from uuid import UUID
from app.config import get_settings

settings = get_settings()

_bearer = HTTPBearer()


class CurrentUser(BaseModel):
    id: UUID
    email: str
    role: str = "authenticated"


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
) -> CurrentUser:
    """
    Decode and validate the Supabase JWT from the Authorization: Bearer header.
    Raises 401 for invalid / expired tokens.
    """
    token = credentials.credentials
    try:
        payload = jwt.decode(
            token,
            settings.supabase_jwt_secret,
            algorithms=["HS256"],
            options={"verify_aud": False},   # Supabase sets aud: "authenticated"
        )
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid or expired token: {exc}",
            headers={"WWW-Authenticate": "Bearer"},
        )

    sub = payload.get("sub")
    email = payload.get("email", "")
    role = payload.get("role", "authenticated")

    if not sub:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing subject claim",
        )

    return CurrentUser(id=UUID(sub), email=email, role=role)


# Convenience alias used in routers
AuthDep = Depends(get_current_user)

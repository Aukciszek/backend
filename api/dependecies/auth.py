from datetime import datetime, timedelta, timezone
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext

from api.config import ALGORITHM, SECRET_KEYS_JWT, SERVER_ID, SERVERS
from api.dependecies.supabase import supabase
from api.models.parsers import TokenData

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def create_access_tokens(data: dict, expires_delta: timedelta | None = None):
    """
    Generates a JWT access token.
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})

    encoded_jwt = []
    # Check if SECRET_KEYS_JWT is iterable
    if isinstance(SECRET_KEYS_JWT, (list, tuple)):
        for i, secret_key_jwt in enumerate(SECRET_KEYS_JWT):
            # Check if SERVERS is iterable and has enough items
            server = (
                SERVERS[i]
                if isinstance(SERVERS, (list, tuple)) and i < len(SERVERS)
                else None
            )
            encoded_jwt.append(
                {
                    "access_token": jwt.encode(
                        to_encode,
                        secret_key_jwt,
                        algorithm=str(ALGORITHM) if ALGORITHM else None,
                    ),
                    "server": server,
                }
            )

    return encoded_jwt


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    return pwd_context.hash(password)


def authenticate_user(email: str, password: str):
    user = supabase.table("users").select("*").eq("email", email).execute()
    if not user:
        return False
    if not verify_password(password, user.data[0].get("password")):
        return False
    return user


async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid authentication credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        if not isinstance(SECRET_KEYS_JWT, (list, tuple)) or not SECRET_KEYS_JWT:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Invalid SECRET_KEYS_JWT configuration",
            )
        payload = jwt.decode(
            token, SECRET_KEYS_JWT[SERVER_ID], algorithms=[str(ALGORITHM)]
        )
        uid = payload.get("uid")
        if uid is None:
            raise credentials_exception
        is_admin = payload.get("isAdmin")
        if is_admin is None:
            raise credentials_exception
        token_data = TokenData(uid=uid, isAdmin=is_admin)
    except jwt.InvalidTokenError:
        raise credentials_exception
    return {"uid": token_data.uid, "isAdmin": token_data.isAdmin}

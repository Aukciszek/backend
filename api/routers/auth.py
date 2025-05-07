from datetime import datetime, timedelta, timezone

import jwt
from fastapi import APIRouter, HTTPException, status
from passlib.context import CryptContext

from api.config import ACCESS_TOKEN_EXPIRE_MINUTES, ALGORITHM, SECRET_KEYS_JWT, SERVERS
from api.dependencies import supabase
from api.models.parsers import AuthenticationResponse, LoginData, RegisterData

router = APIRouter(
    prefix="/api/auth",
    tags=["Authentication"],
)

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


def create_access_token(data: dict, expires_delta: timedelta | None = None):
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


@router.post(
    "/register",
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    response_description="User registered successfully.",
    response_model=AuthenticationResponse,
    responses={
        201: {
            "description": "User registered.",
            "content": {
                "application/json": {
                    "example": {
                        "access_tokens": [
                            {"access_token": "token1", "server": "server1"},
                            {"access_token": "token2", "server": "server2"},
                        ],
                        "token_type": "bearer",
                    }
                }
            },
        },
        409: {
            "description": "Email already registered.",
            "content": {
                "application/json": {"example": {"detail": "Email already registered."}}
            },
        },
    },
)
async def register(user_req_data: RegisterData):
    """
    Registers a new user in the system and returns access tokens.

    Request Body:
    - `email`: The email address of the user.
    - `password`: The password of the user.
    - `admin`: Boolean indicating if the user is an administrator.
    """
    user = (
        supabase.table("users").select("*").eq("email", user_req_data.email).execute()
    )

    if user.data == []:
        supabase.table("users").insert(
            {
                "email": user_req_data.email,
                "password": pwd_context.hash(user_req_data.password),
                "admin": user_req_data.admin,
            }
        ).execute()
    else:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Email already registered."
        )

    user = (
        supabase.table("users").select("*").eq("email", user_req_data.email).execute()
    )

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_tokens = create_access_token(
        data={"uid": user.data[0]["uid"], "admin": user.data[0]["admin"]},
        expires_delta=access_token_expires,
    )

    return {"access_tokens": access_tokens, "token_type": "bearer"}


@router.post(
    "/login",
    status_code=status.HTTP_200_OK,
    summary="Login a user",
    response_description="User logged in successfully.",
    response_model=AuthenticationResponse,
    responses={
        200: {
            "description": "User logged in.",
            "content": {
                "application/json": {
                    "example": {
                        "access_tokens": [
                            {"access_token": "token1", "server": "server1"},
                            {"access_token": "token2", "server": "server2"},
                        ],
                        "token_type": "bearer",
                    }
                }
            },
        },
        401: {
            "description": "Incorrect email or password.",
            "content": {
                "application/json": {
                    "example": {"detail": "Incorrect email or password."}
                }
            },
        },
    },
)
async def login(user_req_data: LoginData):
    """
    Logs in a user and returns an access tokens.

    Request Body:
    - `email`: The email address of the user.
    - `password`: The password of the user.
    """
    user = (
        supabase.table("users").select("*").eq("email", user_req_data.email).execute()
    )

    if user.data == []:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
        )
    elif not pwd_context.verify(user_req_data.password, user.data[0]["password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
        )

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    access_tokens = create_access_token(
        data={"uid": user.data[0]["uid"], "admin": user.data[0]["admin"]},
        expires_delta=access_token_expires,
    )

    return {"access_tokens": access_tokens, "token_type": "bearer"}

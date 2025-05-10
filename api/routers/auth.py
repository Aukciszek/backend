from datetime import timedelta

from fastapi import APIRouter, HTTPException, status

from api.config import ACCESS_TOKEN_EXPIRE_MINUTES
from api.dependecies.auth import authenticate_user, create_access_tokens, pwd_context
from api.dependecies.supabase import supabase
from api.models.parsers import AuthenticationResponse, LoginData, RegisterData

router = APIRouter(
    prefix="/api/auth",
    tags=["Authentication"],
)


@router.post(
    "/register",
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    response_description="User registered successfully.",
    response_model=AuthenticationResponse,
    responses={
        201: {
            "description": "User registered successfully.",
            "content": {
                "application/json": {
                    "example": {
                        "access_tokens": [
                            {
                                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                                "server": "server1",
                            },
                            {
                                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                                "server": "server2",
                            },
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
    - `is_admin`: Boolean indicating if the user is an administrator.
    """
    user = (
        supabase.table("users").select("*").eq("email", user_req_data.email).execute()
    )

    if user.data == []:
        supabase.table("users").insert(
            {
                "email": user_req_data.email,
                "password": pwd_context.hash(user_req_data.password),
                "isAdmin": user_req_data.is_admin,
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
    access_tokens = create_access_tokens(
        data={"uid": user.data[0].get("uid"), "isAdmin": user.data[0].get("isAdmin")},
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
            "description": "User logged in successfully.",
            "content": {
                "application/json": {
                    "example": {
                        "access_tokens": [
                            {
                                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                                "server": "server1",
                            },
                            {
                                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                                "server": "server2",
                            },
                        ],
                        "token_type": "bearer",
                    }
                }
            },
        },
        401: {
            "description": "Authentication failed.",
            "content": {
                "application/json": {
                    "example": {"detail": "Incorrect email or password"}
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
    user = authenticate_user(user_req_data.email, user_req_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    access_tokens = create_access_tokens(
        data={"uid": user.data[0].get("uid"), "isAdmin": user.data[0].get("isAdmin")},
        expires_delta=access_token_expires,
    )

    return {"access_tokens": access_tokens, "token_type": "bearer"}

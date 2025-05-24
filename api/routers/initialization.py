from fastapi import APIRouter, Depends, HTTPException, status

from api.config import SERVERS, state
from api.dependecies.auth import get_current_user
from api.models.parsers import InitialValuesData, InitialValuesResponse, ResultResponse
from api.utils.utils import validate_initialized, validate_not_initialized

router = APIRouter(
    prefix="/api",
    tags=["Initialization"],
)


@router.post(
    "/initial-values",
    status_code=status.HTTP_201_CREATED,
    tags=["Initialization"],
    summary="Set initial values for the MPC protocol",
    response_description="Initial values have been successfully set.",
    response_model=ResultResponse,
    responses={
        201: {
            "description": "Initial values set successfully.",
            "content": {
                "application/json": {"example": {"result": "Initial values set"}}
            },
        },
        400: {
            "description": "Invalid input or configuration.",
            "content": {
                "application/json": {
                    "examples": {
                        "invalid_values": {
                            "value": {"detail": "Invalid t or n values."},
                            "summary": "Invalid values",
                        },
                        "negative_prime": {
                            "value": {"detail": "Prime number must be positive."},
                            "summary": "Invalid prime",
                        },
                        "server_config": {
                            "value": {"detail": "Invalid SERVERS configuration."},
                            "summary": "Invalid server configuration",
                        },
                    }
                }
            },
        },
        403: {
            "description": "Forbidden. User does not have permission.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "You do not have permission to access this resource."
                    }
                }
            },
        },
    },
)
async def set_initial_values(
    values: InitialValuesData, current_user: dict = Depends(get_current_user)
):
    """
    Sets the initial values required for the MPC protocol.

    Request Body:
    - `id`: The ID of this party
    - `p`: The prime number (hexadecimal string)
    """
    if current_user.get("isAdmin") == False:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access this resource.",
        )

    validate_not_initialized(["t", "n", "id", "p", "parties"])

    if not isinstance(SERVERS, (list, tuple)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid SERVERS configuration.",
        )

    n = len(SERVERS)
    t = (n - 1) // 2

    if 2 * t + 1 != n:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid t or n values."
        )

    if int(values.p, 16) <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Prime number must be positive.",
        )

    state.update(
        {
            "t": t,
            "n": n,
            "id": values.id,
            "p": int(values.p, 16),
            "parties": SERVERS,
            "shares": {
                "client_shares": [],
                "shared_r": [None] * n,
                "shared_q": [None] * n,
                "shared_u": [None] * n,
            },
        }
    )

    return {"result": "Initial values set"}


@router.get(
    "/initial-values",
    status_code=status.HTTP_200_OK,
    summary="Get the currently set initial values",
    response_description="Returns the currently set initial values.",
    response_model=InitialValuesResponse,
    responses={
        200: {
            "description": "Successfully retrieved initial values.",
            "content": {
                "application/json": {
                    "example": {
                        "t": 1,
                        "n": 3,
                        "p": "0xfffffffffffffffffffffffffffffffeffffffffffffffff",
                        "parties": [
                            "http://localhost:5001",
                            "http://localhost:5002",
                            "http://localhost:5003",
                        ],
                    }
                }
            },
        },
        400: {
            "description": "Server is not initialized.",
            "content": {
                "application/json": {
                    "example": {"detail": "Server is not initialized."}
                }
            },
        },
        403: {
            "description": "Forbidden. User does not have permission.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "You do not have permission to access this resource."
                    }
                }
            },
        },
    },
)
async def get_initial_values(_: dict = Depends(get_current_user)):
    """
    Returns the currently set initial values.
    """

    validate_initialized(["t", "n", "p", "parties"])

    return {
        "t": state.get("t"),
        "n": state.get("n"),
        "p": hex(state.get("p", 0)),
        "parties": state.get("parties"),
    }

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from api.config import SERVERS, WIREGUARD_IPS, state
from api.dependecies.auth import get_current_user
from api.models.parsers import (
    InitialValuesData,
    InitialValuesResponse,
    ResultResponse,
    TokenData,
)
from api.utils.utils import (
    binary_exponentiation,
    inverse_matrix_mod,
    multiply_matrix,
    validate_initialized,
    validate_not_initialized,
)

router = APIRouter(
    prefix="/api",
    tags=["Initialization"],
)


@router.post(
    "/initial-values",
    status_code=status.HTTP_201_CREATED,
    tags=["Initialization"],
    summary="Set initial MPC protocol values",
    response_description="Initial protocol values have been successfully set.",
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
                        },
                        "negative_prime": {
                            "value": {"detail": "Prime number must be positive."},
                        },
                        "server_config": {
                            "value": {"detail": "Invalid SERVERS configuration."},
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
    values: InitialValuesData,
    current_user: Annotated[TokenData, Depends(get_current_user)],
):
    """
    Sets the initial values for the MPC protocol (party id, prime, and calculated t, n).

    Request Body:
    - `id`: The ID of this party
    - `p`: The prime number (hexadecimal string)
    """
    if not current_user.is_admin:
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
    
    if isinstance(WIREGUARD_IPS, (list, tuple)) and len(WIREGUARD_IPS)==len(SERVERS):
        parties = WIREGUARD_IPS
    else:
        parties = SERVERS

    state.update(
        {
            "t": t,
            "n": n,
            "id": values.id,
            "p": int(values.p, 16),
            "parties": parties,
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
                        "t": 2,
                        "n": 5,
                        "p": "0x35",
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
                "application/json": {"example": {"detail": "n is not initialized."}}
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
async def get_initial_values(_: Annotated[TokenData, Depends(get_current_user)]):
    """
    Returns the currently set initial values.
    """

    validate_initialized(["t", "n", "p", "parties"])

    return {
        "t": state.get("t", 0),
        "n": state.get("n", 0),
        "p": hex(state.get("p", 0)),
        "parties": state.get("parties", []),
    }


@router.put(
    "/calculate-A",
    status_code=status.HTTP_201_CREATED,
    summary="Calculate matrix A for MPC protocol",
    response_description="Matrix A computed via modular inversion and matrix multiplication.",
    response_model=ResultResponse,
    responses={
        201: {
            "description": "Matrix A calculated successfully.",
            "content": {
                "application/json": {"example": {"result": "Matrix A calculated"}}
            },
        },
        400: {
            "description": "Invalid input or server not initialized.",
            "content": {
                "application/json": {
                    "examples": {
                        "server_not_initialized": {
                            "value": {"detail": "n is not initialized."},
                        }
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
async def calculate_A(current_user: Annotated[TokenData, Depends(get_current_user)]):
    """
    Calculates matrix A using the inverse of a generated matrix B and modular operations.
    """

    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access this resource.",
        )

    validate_initialized(["t", "n", "p"])
    validate_not_initialized(["A"])

    # Generate matrix B
    B = [list(range(1, state.get("n", 0) + 1)) for _ in range(state.get("n", 0))]
    for j in range(state.get("n", 0)):
        for k in range(state.get("n", 0)):
            B[j][k] = binary_exponentiation(B[j][k], j, state.get("p", 0))

    # Compute inverse of B
    B_inv = inverse_matrix_mod(B, state.get("p", 0))

    # Generate matrix P
    P = [[0] * state.get("n", 0) for _ in range(state.get("n", 0))]
    for i in range(state.get("t", 0)):
        P[i][i] = 1

    # Compute matrix A
    state["A"] = multiply_matrix(
        multiply_matrix(B_inv, P, state.get("p", 0)), B, state.get("p", 0)
    )

    return {"result": "Matrix A calculated successfully."}

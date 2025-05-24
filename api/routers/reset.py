from fastapi import APIRouter, Depends, HTTPException, status

from api.config import state
from api.dependecies.auth import get_current_user
from api.models.parsers import ResultResponse
from api.utils.utils import validate_initialized

router = APIRouter(
    prefix="/api",
    tags=["Reset"],
)


@router.post(
    "/reset-calculation",
    status_code=status.HTTP_201_CREATED,
    summary="Reset calculation values",
    response_description="Calculation parameters and temporary share values have been cleared.",
    response_model=ResultResponse,
    responses={
        201: {
            "description": "Calculation reset successful.",
            "content": {
                "application/json": {
                    "example": {"result": "Reset calculation successful"}
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
async def reset_calculation(current_user: dict = Depends(get_current_user)):
    """
    Clears temporary calculation values (multiplicative_share, additive_share, xor_share).
    """
    if current_user.get("isAdmin") == False:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access this resource.",
        )

    validate_initialized(["n"])

    state.update(
        {
            # temporary results of arithmetic operations on shares
            "multiplicative_share": None,
            "additive_share": None,
            "xor_share": None,
        }
    )

    state["shares"].update(
        {
            "shared_r": [None] * state.get("n", 0),
            "shared_q": [None] * state.get("n", 0),
        }
    )

    return {"result": "Reset calculation successful"}


@router.post(
    "/reset-comparison",
    status_code=status.HTTP_201_CREATED,
    summary="Reset comparison values",
    response_description="Comparison-specific shares and tables reset to their initial state.",
    response_model=ResultResponse,
    responses={
        201: {
            "description": "Comparison reset successful.",
            "content": {
                "application/json": {
                    "example": {"result": "Reset comparison successful"}
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
async def reset_comparison(current_user: dict = Depends(get_current_user)):
    """
    Resets all values related to the comparison protocol.
    """
    if current_user.get("isAdmin") == False:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access this resource.",
        )

    validate_initialized(["n"])

    state.update(
        {
            "multiplicative_share": None,
            "additive_share": None,
            "xor_share": None,
            "random_number_bit_shares": [],
            "random_number_share": None,
            "comparison_a": None,
            "z_table": [],
            "Z_table": [],
            "comparison_a_bits": [],
        }
    )

    state["shares"].update(
        {
            "shared_r": [None] * state["n"],
            "shared_q": [None] * state["n"],
            "shared_u": [None] * state["n"],
            "u": None,
            "v": None,
        }
    )

    return {"result": "Reset comparison successful"}


@router.post(
    "/factory-reset",
    status_code=status.HTTP_201_CREATED,
    summary="Perform a factory reset",
    response_description="All server parameters and shares have been reset to uninitialized state.",
    response_model=ResultResponse,
    responses={
        201: {
            "description": "Factory reset successful.",
            "content": {
                "application/json": {"example": {"result": "Factory reset successful"}}
            },
        },
        400: {"description": "Invalid request."},
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
async def factory_reset(current_user: dict = Depends(get_current_user)):
    """
    Performs a full reset of the server state to its initial, uninitialized configuration.
    """
    if current_user.get("isAdmin") == False:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access this resource.",
        )

    state.update(
        {
            "t": None,
            "n": None,
            "id": None,
            "p": None,
            "parties": None,
            "multiplicative_share": None,
            "additive_share": None,
            "xor_share": None,
            "shares": {
                "client_shares": None,
                "shared_r": None,
                "shared_q": None,
                "shared_u": None,
                "u": None,
                "v": None,
            },
            "A": None,
            "random_number_bit_shares": [],
            "random_number_share": None,
            "comparison_a": None,
            "z_table": [],
            "Z_table": [],
            "comparison_a_bits": [],
        }
    )

    return {"result": "Factory reset successful"}

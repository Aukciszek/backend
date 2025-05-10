from fastapi import APIRouter, Depends, HTTPException, status

from api.config import STATUS, state
from api.dependecies.auth import get_current_user
from api.models.parsers import ResultResponse
from api.utils.utils import reset_state, validate_initialized

router = APIRouter(
    prefix="/api",
    tags=["Reset"],
)


@router.post(
    "/reset-calculation",
    status_code=status.HTTP_201_CREATED,
    summary="Reset the calculation",
    response_description="Calculation has been reset.",
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
async def reset_calculation(current_user: dict = Depends(get_current_user)):
    """
    Resets the calculation, clearing intermediate values.
    """
    if current_user.get("isAdmin") == False:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access this resource.",
        )

    if state.get("status") == STATUS.NOT_INITIALIZED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Server is not initialized."
        )

    validate_initialized(["n"])

    reset_state(["calculated_share", "xor_multiplication"])

    state.update(
        {
            "shared_q": [None] * state.get("n", 0),
            "shared_r": [None] * state.get("n", 0),
            "status": STATUS.INITIALIZED,
        }
    )

    return {"result": "Reset calculation successful"}


@router.post(
    "/reset-comparison",
    status_code=status.HTTP_201_CREATED,
    summary="Reset the comparison",
    response_description="Comparison has been reset.",
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
async def reset_comparison(current_user: dict = Depends(get_current_user)):
    """
    Resets the comparison, clearing comparison-specific values.
    """
    if current_user.get("isAdmin") == False:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access this resource.",
        )

    if state.get("status") == STATUS.NOT_INITIALIZED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Server is not initialized."
        )

    validate_initialized(["n"])

    reset_state(["calculated_share", "zZ", "xor_multiplication", "temporary_zZ"])

    state.update(
        {
            "shared_q": [None] * state.get("n", 0),
            "shared_r": [None] * state.get("n", 0),
        }
    )

    state.update({"status": STATUS.INITIALIZED})
    return {"result": "Reset comparison successful"}


@router.post(
    "/factory-reset",
    status_code=status.HTTP_201_CREATED,
    summary="Perform a factory reset",
    response_description="Server has been factory reset.",
    response_model=ResultResponse,
    responses={
        201: {
            "description": "Factory reset successful.",
            "content": {
                "application/json": {"example": {"result": "Factory reset successful"}}
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
async def factory_reset(current_user: dict = Depends(get_current_user)):
    """
    Resets the server to its initial, uninitialized state.
    """
    if current_user.get("isAdmin") == False:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access this resource.",
        )

    reset_state(
        [
            "t",
            "n",
            "id",
            "p",
            "parties",
            "shared_q",
            "shared_r",
            "client_shares",
            "calculated_share",
            "xor_multiplication",
            "temporary_zZ",
            "zZ",
        ]
    )

    state.update({"status": STATUS.NOT_INITIALIZED})
    return {"result": "Factory reset successful"}

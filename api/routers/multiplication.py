from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from api.config import state
from api.dependecies.auth import get_current_user
from api.models.parsers import ResultResponse, TokenData
from api.utils.utils import validate_initialized, validate_initialized_shares_array

router = APIRouter(
    prefix="/api",
    tags=["Multiplication"],
)


@router.put(
    "/calculate-multiplicative-share",
    status_code=status.HTTP_201_CREATED,
    summary="Calculate multiplicative share",
    response_description="Multiplicative share computed as the modulo sum of all received r shares.",
    response_model=ResultResponse,
    responses={
        201: {
            "description": "Multiplicative share calculated successfully.",
            "content": {
                "application/json": {
                    "example": {"result": "Multiplicative share calculated"}
                }
            },
        },
        400: {
            "description": "Server is not initialized or shares are not provided.",
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
async def calculate_multiplicative_share(
    current_user: Annotated[TokenData, Depends(get_current_user)],
):
    """
    Calculates the multiplicative share as the sum of the shared_r values modulo p.
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access this resource.",
        )

    validate_initialized(["n", "p"])
    validate_initialized_shares_array(["shared_r"])

    state["multiplicative_share"] = sum(
        [
            state.get("shares", {}).get("shared_r", 0)[i]
            for i in range(state.get("n", 0))
        ]
    ) % state.get("p", 0)

    return {"result": "Multiplicative share calculated"}

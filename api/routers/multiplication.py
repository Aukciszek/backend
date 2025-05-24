from fastapi import APIRouter, Depends, HTTPException, status

from api.config import state
from api.dependecies.auth import get_current_user
from api.models.parsers import ResultResponse

router = APIRouter(
    prefix="/api",
    tags=["Multiplication"],
)


@router.put(
    "/calculate-multiplicative-share",
    status_code=status.HTTP_201_CREATED,
    summary="Calculate multiplicative share",
    response_description="Multiplicative share has been calculated.",
    response_model=ResultResponse,
    responses={
        201: {
            "description": "Multiplicative share calculated.",
            "content": {
                "application/json": {
                    "example": {"result": "Multiplicative share calculated"}
                }
            },
        },
        400: {
            "description": "Invalid request.",
            "content": {
                "application/json": {
                    "examples": {
                        "invalid_state": {
                            "value": {
                                "detail": "Server must be in r calculated and shared state."
                            },
                            "summary": "Invalid server state",
                        },
                        "missing_params": {
                            "value": {
                                "detail": "set_in_temporary_zZ_index must be provided when calculate_for_xor is False."
                            },
                            "summary": "Missing parameter",
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
async def calculate_multiplicative_share(
    current_user: dict = Depends(get_current_user),
):
    """
    Calculates a multiplicative share used in secure multiplication protocols.
    """
    if current_user.get("isAdmin") == False:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access this resource.",
        )

    state["multiplicative_share"] = sum(
        [
            state.get("shares", {}).get("shared_r", 0)[i]
            for i in range(state.get("n", 0))
        ]
    ) % state.get("p", 0)

    return {"result": "Multiplicative share calculated"}

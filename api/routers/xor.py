from fastapi import APIRouter, Depends, HTTPException, status

from api.config import state
from api.dependecies.auth import get_current_user
from api.models.parsers import ResultResponse

router = APIRouter(
    prefix="/api",
    tags=["XOR"],
)


@router.post(
    "/calculate-xor-share",
    status_code=status.HTTP_201_CREATED,
    summary="Perform secure XOR operation",
    response_description="Additive share resulting from XOR operation has been calculated.",
    responses={
        201: {
            "description": "Additive share calculated.",
            "content": {
                "application/json": {"example": {"result": "Additive share calculated"}}
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
async def calculate_xor_share(current_user: dict = Depends(get_current_user)):
    """
    Performs a secure XOR operation on shared values.

    Request Body:
    - `take_value_from_temporary_zZ`: Flag indicating whether to take the second value from temporary_zZ.
    - `zZ_first_multiplication_factor`: The first multiplication factor from zZ.
    - `zZ_second_multiplication_factor`: The second multiplication factor from zZ.
    """
    if current_user.get("isAdmin") == False:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access this resource.",
        )

    state["xor_share"] = (
        state.get("additive_share", 0) - 2 * state.get("multiplicative_share", 0)
    ) % state.get("p", 0)

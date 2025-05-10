from fastapi import APIRouter, Depends, HTTPException, status

from api.config import STATUS, TEMPORARY_Z0, TEMPORARY_Z1, state
from api.dependecies.auth import get_current_user
from api.models.parsers import CalculateMultiplicativeShareData, ResultResponse
from api.utils.utils import (
    get_temporary_zZ,
    reset_temporary_zZ,
    set_temporary_zZ,
    validate_initialized,
    validate_initialized_array,
)

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
    values: CalculateMultiplicativeShareData,
    current_user: dict = Depends(get_current_user),
):
    """
    Calculates a multiplicative share used in secure multiplication protocols.

    Request Body:
    - `set_in_temporary_zZ_index`: Index to set the calculated value in temporary_zZ.
    - `calculate_for_xor`: Flag indicating whether to calculate for XOR.
    """
    if current_user.get("isAdmin") == False:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access this resource.",
        )

    if state.get("status") != STATUS.R_CALC_SHARED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Server must be in r calculated and shared state.",
        )

    validate_initialized(["n", "p"])
    validate_initialized_array(["shared_r"])

    # Check for optional parameters
    if not values.calculate_for_xor:
        if values.set_in_temporary_zZ_index is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="set_in_temporary_zZ_index must be provided when calculate_for_xor is False.",
            )

    calculated_value = sum(
        [state.get("shared_r", [])[i] for i in range(state.get("n", 0))]
    ) % state.get("p", 0)

    if values.calculate_for_xor:
        state.update({"xor_multiplication": calculated_value})
    else:
        set_temporary_zZ(values.set_in_temporary_zZ_index, calculated_value)

    return {"result": "Multiplicative share calculated"}


@router.post(
    "/pop-zZ",
    status_code=status.HTTP_201_CREATED,
    summary="Pop a value from zZ",
    response_description="Value has been popped from zZ.",
    response_model=ResultResponse,
    responses={
        201: {
            "description": "zZ popped successfully.",
            "content": {"application/json": {"example": {"result": "zZ popped"}}},
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
async def pop_zZ(current_user: dict = Depends(get_current_user)):
    """
    Pops a value from the zZ.
    """
    if current_user.get("isAdmin") == False:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access this resource.",
        )

    state["zZ"][0] = [get_temporary_zZ(TEMPORARY_Z0), get_temporary_zZ(TEMPORARY_Z1)]
    state["zZ"].pop(1)
    reset_temporary_zZ()

    return {"result": "zZ popped"}

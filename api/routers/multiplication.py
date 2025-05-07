from fastapi import APIRouter, HTTPException, status

from api.config import STATUS, TEMPORARY_Z0, TEMPORARY_Z1, state
from api.models.parsers import CalculateMultiplicativeShareData
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
            "description": "Server must be in 'r' calculated and shared state.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Server must be in r calculated and shared state."
                    }
                }
            },
        },
    },
)
async def calculate_multiplicative_share(values: CalculateMultiplicativeShareData):
    """
    Calculates a multiplicative share used in secure multiplication protocols.

    Request Body:
    - `set_in_temporary_zZ_index`: Index to set the calculated value in temporary_zZ.
    - `calculate_for_xor`: Flag indicating whether to calculate for XOR.
    """
    if state["status"] != STATUS.R_CALC_SHARED:
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

    calculated_value = (
        sum([state["shared_r"][i] for i in range(state["n"])]) % state["p"]
    )

    if values.calculate_for_xor:
        state["xor_multiplication"] = calculated_value
    else:
        set_temporary_zZ(values.set_in_temporary_zZ_index, calculated_value)

    return {"result": "Multiplicative share calculated"}


@router.post(
    "/pop-zZ",
    status_code=status.HTTP_201_CREATED,
    summary="Pop a value from zZ",
    response_description="Value has been popped from zZ.",
    responses={
        201: {
            "description": "zZ popped.",
            "content": {"application/json": {"example": {"result": "zZ popped"}}},
        }
    },
)
async def pop_zZ():
    """
    Pops a value from the zZ.
    """
    state["zZ"][0] = [get_temporary_zZ(TEMPORARY_Z0), get_temporary_zZ(TEMPORARY_Z1)]
    state["zZ"].pop(1)
    reset_temporary_zZ()

    return {"result": "zZ popped"}

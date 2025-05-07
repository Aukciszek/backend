from fastapi import APIRouter, HTTPException, status

from api.config import STATUS, state
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
        }
    },
)
async def reset_calculation():
    """
    Resets the calculation, clearing intermediate values.
    """
    if state["status"] == STATUS.NOT_INITIALIZED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Server is not initialized."
        )

    validate_initialized(["n"])

    reset_state(["calculated_share", "xor_multiplication"])
    state["shared_q"] = [None] * state["n"]
    state["shared_r"] = [None] * state["n"]
    state["status"] = STATUS.INITIALIZED

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
        }
    },
)
async def reset_comparison():
    """
    Resets the comparison, clearing comparison-specific values.
    """
    if state["status"] == STATUS.NOT_INITIALIZED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Server is not initialized."
        )

    validate_initialized(["n"])

    reset_state(["calculated_share", "zZ", "xor_multiplication", "temporary_zZ"])

    state["shared_q"] = [None] * state["n"]
    state["shared_r"] = [None] * state["n"]

    state["status"] = STATUS.INITIALIZED

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
        }
    },
)
async def factory_reset():
    """
    Resets the server to its initial, uninitialized state.
    """
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

    state["status"] = STATUS.NOT_INITIALIZED

    return {"result": "Factory reset successful"}

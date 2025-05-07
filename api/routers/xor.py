from fastapi import APIRouter, status

from api.config import TEMPORARY_Z1, state
from api.models.parsers import ResultResponse, XorData
from api.utils.utils import get_temporary_zZ, set_temporary_zZ

router = APIRouter(
    prefix="/api",
    tags=["XOR"],
)


@router.post(
    "/xor",
    status_code=status.HTTP_201_CREATED,
    summary="Perform secure XOR operation",
    response_description="Additive share resulting from XOR operation has been calculated.",
    response_model=ResultResponse,
    responses={
        201: {
            "description": "Additive share calculated.",
            "content": {
                "application/json": {"example": {"result": "Additive share calculated"}}
            },
        },
        # 400: {"description": "Server must be in initialized state.", "content": {"application/json": {"example": {"detail": "Server must be in initialized state."}}}}, #TODO
    },
)
async def addition(values: XorData):
    """
    Performs a secure XOR operation on shared values.

    Request Body:
    - `take_value_from_temporary_zZ`: Flag indicating whether to take the second value from temporary_zZ.
    - `zZ_first_multiplication_factor`: The first multiplication factor from zZ.
    - `zZ_second_multiplication_factor`: The second multiplication factor from zZ.
    """
    # Validate server state
    # if state["status"] != STATUS.INITIALIZED:
    #     raise HTTPException(
    #         status_code=400, detail="Server must be in initialized state."
    #     ) TODO

    # Extract the first multiplication factor
    first_multiplication_factor = state["zZ"][values.zZ_first_multiplication_factor[0]][
        values.zZ_first_multiplication_factor[1]
    ]

    # Extract the second multiplication factor based on the condition
    second_multiplication_factor = (
        get_temporary_zZ(values.zZ_second_multiplication_factor[0])
        if values.take_value_from_temporary_zZ
        else state["zZ"][values.zZ_second_multiplication_factor[0]][
            values.zZ_second_multiplication_factor[1]
        ]
    )

    # Calculate the result and update state
    result = (
        first_multiplication_factor
        + second_multiplication_factor
        - 2 * state["xor_multiplication"]
    )
    set_temporary_zZ(TEMPORARY_Z1, result)

    return {"result": "Additive share calculated"}

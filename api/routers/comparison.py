from fastapi import APIRouter, Depends, HTTPException, status

from api.config import STATUS, state
from api.dependecies.auth import get_current_user
from api.models.parsers import (
    AComparisonData,
    CalculatedComparisonResultData,
    ResultResponse,
    ZComparisonData,
)
from api.utils.utils import binary, reset_temporary_zZ

router = APIRouter(
    prefix="/api",
    tags=["Comparison"],
)


@router.post(
    "/calculate-a-comparison",
    status_code=status.HTTP_201_CREATED,
    summary="Calculate 'A' for comparison",
    response_description="'A' for comparison has been calculated.",
    response_model=ResultResponse,
    responses={
        201: {
            "description": "'A' for comparison calculated.",
            "content": {
                "application/json": {
                    "example": {"result": "'A' for comparison calculated"}
                }
            },
        },
        400: {
            "description": "Invalid input or not enough shares.",
            "content": {
                "application/json": {
                    "examples": {
                        "not_enough_shares": {
                            "value": {
                                "detail": "At least two client shares must be configured."
                            }
                        },
                        "same_client": {
                            "value": {"detail": "Client IDs must be different."}
                        },
                        "missing_shares": {
                            "value": {
                                "detail": "Shares not set for one or both clients."
                            }
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
async def calculate_a_comparison(
    values: AComparisonData, current_user: dict = Depends(get_current_user)
):
    """
    Calculates the 'A' value required for the comparison protocol.

    Request Body:
    - `first_client_id`: The ID of the first client.
    - `second_client_id`: The ID of the second client.
    """
    if current_user.get("isAdmin") == False:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access this resource.",
        )

    if len(state.get("client_shares", [])) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least two client shares must be configured.",
        )

    if values.first_client_id == values.second_client_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Client IDs must be different.",
        )

    first_client_share = next(
        (y for x, y in state.get("client_shares", []) if x == values.first_client_id),
        None,
    )
    second_client_share = next(
        (y for x, y in state.get("client_shares", []) if x == values.second_client_id),
        None,
    )

    if first_client_share is None or second_client_share is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Shares not set for one or both clients.",
        )

    state.update(
        {
            "calculated_share":
            # pow(2, values.l + values.k + 2)
            # + pow(2, values.l)
            first_client_share
            - second_client_share
        }
    )

    state.update({"status": STATUS.SHARE_CALCULATED})
    return {"result": "'A' for comparison calculated"}


@router.post(
    "/calculate-z-comparison",
    status_code=status.HTTP_201_CREATED,
    summary="Calculate 'Z' for comparison",
    response_description="'Z' for comparison has been calculated.",
    response_model=ResultResponse,
    responses={
        201: {
            "description": "'Z' for comparison calculated.",
            "content": {
                "application/json": {
                    "example": {"result": "'Z' for comparison calculated"}
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
async def calculate_z(
    values: ZComparisonData, current_user: dict = Depends(get_current_user)
):
    """
    Calculates the 'Z' value required for the comparison protocol.

    Request Body:
    - `opened_a`: Opened value of a (hexadecimal string)
    - `l`: length
    - `k`: kappa
    """
    if current_user.get("isAdmin") == False:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access this resource.",
        )

    a_bin = binary(int(values.opened_a, 16))

    while len(a_bin) < values.l + values.k + 2:
        a_bin.append(0)

    zZ = []

    for i in range(values.l):
        zZ.append([a_bin[i], a_bin[i]])

    zZ = list(reversed(zZ))
    zZ.append([0, 0])

    state.update({"zZ": zZ})
    reset_temporary_zZ()
    return {"result": "'Z' for comparison calculated"}


@router.post(
    "/calculate-comparison-result",
    status_code=status.HTTP_201_CREATED,
    summary="Calculate the final comparison result",
    response_description="Final comparison result has been calculated.",
    response_model=ResultResponse,
    responses={
        201: {
            "description": "Comparison result calculated.",
            "content": {
                "application/json": {
                    "example": {"result": "Comparison result calculated"}
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
async def calculate_comparison_result(
    values: CalculatedComparisonResultData,
    current_user: dict = Depends(get_current_user),
):
    """
    Calculates the final result of the comparison.

    Request Body:
    - `opened_a`: Opened value of a (hexadecimal string)
    - `l`: length
    - `k`: kappa
    """
    if current_user.get("isAdmin") == False:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access this resource.",
        )

    a_bin = binary(int(values.opened_a, 16))

    while len(a_bin) < values.l + values.k + 2:
        a_bin.append(0)

    state.update(
        {
            "calculated_share": a_bin[values.l]
            + state.get("zZ", [])[0][1]
            - 2 * state.get("xor_multiplication", 0),
            "status": STATUS.SHARE_CALCULATED,
        }
    )
    return {"result": "Comparison result calculated"}

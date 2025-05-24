from fastapi import APIRouter, Depends, HTTPException, status

from api.config import state
from api.dependecies.auth import get_current_user
from api.models.parsers import (
    AComparisonData,
    CalculatedComparisonResultData,
    ResultResponse,
    ZComparisonData,
)
from api.utils.utils import binary

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

    if len(state.get("shares", {}).get("client_shares", [])) < 2:
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
        (
            y
            for x, y in state.get("shares", {}).get("client_shares", [])
            if x == values.first_client_id
        ),
        None,
    )
    second_client_share = next(
        (
            y
            for x, y in state.get("shares", {}).get("client_shares", [])
            if x == values.second_client_id
        ),
        None,
    )

    if first_client_share is None or second_client_share is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Shares not set for one or both clients.",
        )

    state["shares"]["comparison_a"] = (
        pow(2, values.l + values.k + 1)
        - state.get("random_number_share", 0)
        + pow(2, values.l)
        + first_client_share
        - second_client_share
    )

    return {"result": "'a' for comparison calculated"}

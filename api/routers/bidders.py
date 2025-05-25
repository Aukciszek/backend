from fastapi import APIRouter, Depends, HTTPException, status

from api.config import state
from api.dependecies.auth import get_current_user
from api.models.parsers import BiddersResponse
from api.utils.utils import validate_initialized, validate_initialized_shares

router = APIRouter(
    prefix="/api",
    tags=["Bidders"],
)


@router.get(
    "/get-bidders",
    status_code=status.HTTP_200_OK,
    summary="Get list of bidder IDs",
    response_description="Returns a list of client IDs that have provided shares.",
    response_model=BiddersResponse,
    responses={
        200: {
            "description": "Bidder list retrieved successfully.",
            "content": {"application/json": {"example": {"bidders": [1, 2, 3]}}},
        },
        400: {
            "description": "Server is not initialized.",
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
async def get_bidders(current_user: dict = Depends(get_current_user)):
    """
    Retrieves the list of bidder IDs based on the available client shares.
    """
    if current_user.get("isAdmin") == False:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access this resource.",
        )

    validate_initialized(["n"])
    validate_initialized_shares(["client_shares"])

    bidders = sorted([item[0] for item in state.get("shares", {}).get("client_shares", [])])

    return {"bidders": bidders}

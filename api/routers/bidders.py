from fastapi import APIRouter, Depends, HTTPException, status

from api.config import STATUS, state
from api.dependecies.auth import get_current_user
from api.models.parsers import BiddersResponse
from api.utils.utils import validate_initialized

router = APIRouter(
    prefix="/api",
    tags=["Bidders"],
)


@router.get(
    "/get-bidders",
    status_code=status.HTTP_200_OK,
    summary="Get the list of bidders",
    response_description="Returns a list of bidder IDs.",
    response_model=BiddersResponse,
    responses={
        200: {
            "description": "List of bidders retrieved successfully.",
            "content": {"application/json": {"example": {"bidders": [1, 2, 3]}}},
        },
        400: {
            "description": "Server is not initialized.",
            "content": {
                "application/json": {
                    "example": {"detail": "Server is not initialized."}
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
async def get_bidders(current_user: dict = Depends(get_current_user)):
    """
    Retrieves the list of bidders (client IDs) who have submitted shares.
    """
    if current_user.get("isAdmin") == False:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access this resource.",
        )

    if state.get("status") == STATUS.NOT_INITIALIZED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Server is not initialized."
        )

    validate_initialized(["n"])

    bidders = [item[0] for item in state.get("client_shares", [])]

    return {"bidders": bidders}

from fastapi import APIRouter, HTTPException, status

from api.config import STATUS, state
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
    responses={
        200: {
            "description": "List of bidders retrieved.",
            "content": {"application/json": {"example": {"bidders": [1, 2, 3]}}},
        }
    },
)
async def get_bidders():
    """
    Retrieves the list of bidders (client IDs) who have submitted shares.
    """
    if state["status"] == STATUS.NOT_INITIALIZED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Server is not initialized."
        )

    validate_initialized(["n"])

    bidders = [item[0] for item in state["client_shares"]]

    return {"bidders": bidders}

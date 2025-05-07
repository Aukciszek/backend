from fastapi import APIRouter, HTTPException, status

from api.config import state
from api.models.parsers import ShareData
from api.utils.utils import validate_initialized

router = APIRouter(
    prefix="/api",
    tags=["Shares"],
)


@router.post(
    "/set-shares",
    status_code=status.HTTP_201_CREATED,
    summary="Set a client's share",
    response_description="Client's share has been successfully set.",
    responses={
        201: {
            "description": "Shares set successfully.",
            "content": {"application/json": {"example": {"result": "Shares set"}}},
        },
        400: {
            "description": "Shares already set for this client.",
            "content": {
                "application/json": {
                    "example": {"detail": "Shares already set for this client."}
                }
            },
        },
    },
)
async def set_shares(values: ShareData):
    """
    Sets a client's share.

    Request Body:
    - `client_id`: The ID of the client
    - `share`: The share value (hexadecimal string)
    """
    validate_initialized(["client_shares"])

    if (
        next((x for x, _ in state["client_shares"] if x == values.client_id), None)
        is not None
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Shares already set for this client.",
        )

    state["client_shares"].append((values.client_id, int(values.share, 16)))

    return {"result": "Shares set"}

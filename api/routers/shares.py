from fastapi import APIRouter, Depends, HTTPException, status

from api.config import state
from api.dependecies.auth import get_current_user
from api.models.parsers import ResultResponse, SetClientShareData
from api.utils.utils import validate_initialized

router = APIRouter(
    prefix="/api",
    tags=["Shares"],
)


@router.post(
    "/set-client-shares",
    status_code=status.HTTP_201_CREATED,
    summary="Set a client's share",
    response_description="Client's share has been successfully set.",
    response_model=ResultResponse,
    responses={
        201: {
            "description": "Shares set successfully.",
            "content": {"application/json": {"example": {"result": "Shares set"}}},
        },
        400: {
            "description": "Invalid request.",
            "content": {
                "application/json": {
                    "examples": {
                        "already_set": {
                            "value": {"detail": "Shares already set for this client."},
                            "summary": "Shares already set",
                        },
                        "not_initialized": {
                            "value": {"detail": "Server is not initialized."},
                            "summary": "Not initialized",
                        },
                    }
                }
            },
        },
        403: {
            "description": "Forbidden. Only clients can set shares.",
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
async def set_client_shares(
    values: SetClientShareData, current_user: dict = Depends(get_current_user)
):
    """
    Sets a client's share.

    Request Body:
    - `client_id`: The ID of the client
    - `share`: The share value (hexadecimal string)
    """
    if current_user.get("isAdmin") == True:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access this resource.",
        )

    if state.get("shares", {}).get("client_shares") is None:
        state["shares"]["client_shares"] = []

    if (
        next(
            (
                x
                for x, _ in state.get("shares", {}).get("clientP_shares", [])
                if x == current_user.get("uid")
            ),
            None,
        )
        is not None
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Shares already set for this client.",
        )

    state["shares"]["client_shares"].append(
        (current_user.get("uid"), int(values.share, 16))
    )
    return {"result": "Shares set"}

from fastapi import APIRouter, Depends, HTTPException, status

from api.config import state
from api.dependecies.auth import get_current_user
from api.models.parsers import StatusResponse

router = APIRouter(
    prefix="/api",
    tags=["Status"],
)


@router.get(
    "/status",
    status_code=status.HTTP_200_OK,
    summary="Get the current server status",
    response_description="Returns the current status of the server.",
    response_model=StatusResponse,
    responses={
        200: {
            "description": "Server status retrieved successfully.",
            "content": {
                "application/json": {
                    "examples": {
                        "not_initialized": {
                            "value": {"status": "NOT_INITIALIZED"},
                            "summary": "Server not initialized",
                        },
                        "initialized": {
                            "value": {"status": "INITIALIZED"},
                            "summary": "Server initialized",
                        },
                        "other_states": {
                            "value": {"status": "SHARE_CALCULATED"},
                            "summary": "Other possible states",
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
async def get_status(current_user: dict = Depends(get_current_user)):
    """
    Returns the current status of the server.
    """
    if current_user.get("isAdmin") == False:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access this resource.",
        )

    status_value = state.get("status")
    return {"status": status_value.value if status_value is not None else "UNKNOWN"}

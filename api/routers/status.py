from fastapi import APIRouter, status

from api.config import state

router = APIRouter(
    prefix="/api",
    tags=["Status"],
)


@router.get(
    "/status",
    status_code=status.HTTP_200_OK,
    summary="Get the current server status",
    response_description="Returns the current status of the server.",
    responses={
        200: {
            "description": "Server is operational.",
            "content": {"application/json": {"example": {"status": "NOT_INITIALIZED"}}},
        }
    },
)
async def get_status():
    """
    Returns the current status of the server.
    """
    return {"status": state["status"].value}

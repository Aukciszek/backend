from fastapi import APIRouter, status

from api.models.parsers import StatusResponse

router = APIRouter(
    prefix="/api",
    tags=["Status"],
)

@router.get("/status", status_code=status.HTTP_200_OK,
summary="Get status of the server",
response_description="Status of the server",
response_model=StatusResponse,
responses={
    200: {
        "description": "Status of the server",
        "content": {
            "application/json": {
                "example": {
                    "status": "OK"
                }
            }
        },
    },
    400: {"description": "Invalid request."},
},
)
async def get_status():
    return { "status": "OK" }

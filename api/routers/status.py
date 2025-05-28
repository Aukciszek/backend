from fastapi import APIRouter, Request, status

from api.models.parsers import StatusResponse

router = APIRouter(
    prefix="/api",
    tags=["Status"],
)


@router.get(
    "/status",
    status_code=status.HTTP_200_OK,
    summary="Get status of the server",
    response_description="Status of the server",
    response_model=StatusResponse,
    responses={
        200: {
            "description": "Status of the server",
            "content": {"application/json": {"example": {"status": "OK"}}},
        },
        400: {"description": "Invalid request."},
    },
)
async def get_status(request: Request):
    # TODO: Delete

    if request.client:
        print(request.client.host)
    else:
        print("No client information available")

    return {"status": "OK"}

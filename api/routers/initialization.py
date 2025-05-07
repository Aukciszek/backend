from fastapi import APIRouter, HTTPException, status

from api.config import STATUS, state
from api.models.parsers import InitialValues
from api.utils.utils import validate_initialized, validate_not_initialized

router = APIRouter(
    prefix="/api",
    tags=["Initialization"],
)


@router.post(
    "/initial-values",
    status_code=status.HTTP_201_CREATED,
    tags=["Initialization"],
    summary="Set initial values for the MPC protocol",
    response_description="Initial values have been successfully set.",
    responses={
        200: {
            "description": "Initial values set successfully.",
            "content": {
                "application/json": {"example": {"result": "Initial values set"}}
            },
        },
        400: {
            "description": "Invalid input values.",
            "content": {
                "application/json": {"example": {"detail": "Invalid t or n values."}}
            },
        },
    },
)
async def set_initial_values(values: InitialValues):
    """
    Sets the initial values required for the MPC protocol.

    Request Body:
    - `t`: The threshold value
    - `n`: The total number of parties
    - `id`: The ID of this party
    - `p`: The prime number (hexadecimal string)
    - `parties`: List of URLs of all parties

    """
    validate_not_initialized(
        ["t", "n", "id", "p", "shared_q", "shared_r", "parties", "client_shares"]
    )

    if values.t <= 0 or values.n <= 0 or 2 * values.t + 1 != values.n:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid t or n values."
        )

    if int(values.p, 16) <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Prime number must be positive.",
        )

    if len(values.parties) != values.n:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Number of parties does not match n.",
        )

    state.update(
        {
            "t": values.t,
            "n": values.n,
            "id": values.id,
            "p": int(values.p, 16),
            "shared_q": [None] * values.n,
            "shared_r": [None] * values.n,
            "parties": values.parties,
            "client_shares": [],
            "status": STATUS.INITIALIZED,
        }
    )

    return {"result": "Initial values set"}


@router.get(
    "/initial-values",
    status_code=status.HTTP_200_OK,
    summary="Get the currently set initial values",
    response_description="Returns the currently set initial values.",
    responses={
        200: {
            "description": "Successfully retrieved initial values.",
            "content": {
                "application/json": {
                    "example": {
                        "t": 1,
                        "n": 3,
                        "p": "0xfffffffffffffffffffffffffffffffeffffffffffffffff",
                        "parties": [
                            "http://localhost:5001",
                            "http://localhost:5002",
                            "http://localhost:5003",
                        ],
                    }
                }
            },
        },
        400: {
            "description": "Server is not initialized.",
            "content": {
                "application/json": {
                    "example": {"detail": "Server is not initialized."}
                }
            },
        },
    },
)
async def get_initial_values():
    """
    Returns the currently set initial values.
    """
    if state["status"] == STATUS.NOT_INITIALIZED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Server is not initialized."
        )

    validate_initialized(["t", "n", "p", "parties"])

    return {
        "t": state["t"],
        "n": state["n"],
        "p": hex(state["p"]),
        "parties": state["parties"],
    }

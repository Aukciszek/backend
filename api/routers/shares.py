from fastapi import APIRouter, Depends, HTTPException, status

from api.config import state
from api.dependecies.auth import get_current_user
from api.models.parsers import (
    AdditiveShareData,
    ResultResponse,
    SetClientShareData,
    SetShareData,
)
from api.utils.utils import validate_initialized, validate_initialized_shares

router = APIRouter(
    prefix="/api",
    tags=["Shares"],
)


@router.post(
    "/set-client-shares",
    status_code=status.HTTP_201_CREATED,
    summary="Set a client share",
    response_description="Client share set successfully; share value provided in hexadecimal.",
    response_model=ResultResponse,
    responses={
        201: {
            "description": "Client share set successfully.",
            "content": {"application/json": {"example": {"result": "Shares set"}}},
        },
        400: {
            "description": "Invalid request.",
            "content": {
                "application/json": {
                    "example": {"detail": "Shares already set for this client."}
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
    Sets the client's share using the hexadecimal share string from the request.

    Request Body:
    - `client_id`: The ID of the client
    - `share`: The share value (hexadecimal string)
    """
    if current_user.get("isAdmin") == True:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access this resource.",
        )

    validate_initialized_shares(["client_shares"])

    if (
        next(
            (
                x
                for x, _ in state.get("shares", {}).get("client_shares", [])
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


@router.put(
    "/set-multiplicative-share/{share_name}",
    status_code=status.HTTP_201_CREATED,
    summary="Set multiplicative share",
    response_description="Share set from multiplicative share.",
    response_model=ResultResponse,
    responses={
        201: {
            "description": "Share set successfully.",
            "content": {
                "application/json": {
                    "example": {
                        "result": "Share {share_name} set from multiplicative share."
                    }
                }
            },
        },
        400: {
            "description": "Multiplicative share is not initialized.",
            "content": {
                "application/json": {
                    "example": {"detail": "multiplicative_share is not initialized."}
                }
            },
        },
        403: {
            "description": "Forbidden. Only admin users can set this share.",
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
async def set_share_from_multiplicative_share(
    share_name: str, current_user: dict = Depends(get_current_user)
):
    """
    Assigns the calculated multiplicative share to a share with name {share_name}.

    Path Parameters:
    - `share_name`: The name of the share to set
    """
    if current_user.get("isAdmin") == False:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access this resource.",
        )

    validate_initialized(["multiplicative_share"])

    state["shares"][share_name] = state.get("multiplicative_share", 0)

    return {"result": f"Share {share_name} set from multiplicative share."}


@router.post(
    "/set-shares",
    status_code=status.HTTP_201_CREATED,
    summary="Set share",
    response_description="Share set successfully.",
    response_model=ResultResponse,
    responses={
        201: {
            "description": "Share set successfully.",
            "content": {
                "application/json": {
                    "example": {"result": "Share <share_name> set successfully."}
                }
            },
        },
        400: {"description": "Invalid request."},
        403: {
            "description": "Forbidden. Only admin users can set shares.",
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
async def set_shares(
    values: SetShareData, current_user: dict = Depends(get_current_user)
):
    """
    Sets the share value for a given share name.

    Request Body:
    - `share_name`: The name of the share
    - `share_value`: The share value (hexadecimal string)
    """
    if current_user.get("isAdmin") == False:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access this resource.",
        )

    state["shares"][values.share_name] = int(values.share_value, 16)

    return {"result": f"Share {values.share_name} set successfully."}


@router.put(
    "/calculate-additive-share",
    status_code=status.HTTP_201_CREATED,
    summary="Calculate additive share",
    response_description="Additive share calculated successfully.",
    response_model=ResultResponse,
    responses={
        201: {
            "description": "Additive share calculated successfully.",
            "content": {
                "application/json": {
                    "example": {"result": "Additive share calculated successfully."}
                }
            },
        },
        400: {
            "description": "Invalid request. Shares not initialized or invalid share names.",
            "content": {
                "application/json": {
                    "example": {"detail": "Invalid share names provided."}
                }
            },
        },
        403: {
            "description": "Forbidden. Only admin users can calculate shares.",
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
async def calculate_additive_share(
    values: AdditiveShareData, current_user: dict = Depends(get_current_user)
):
    """
    Calculates the additive share from the two provided shares as:
        (first_share + second_share) mod p.

    Request Body:
    - `first_share_name`: The name of the first share
    - `second_share_name`: The name of the second share
    """
    if current_user.get("isAdmin") == False:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access this resource.",
        )

    validate_initialized_shares([values.first_share_name, values.second_share_name])
    validate_initialized(["p"])

    first_share = state.get("shares", {}).get(values.first_share_name, None)
    second_share = state.get("shares", {}).get(values.second_share_name, None)

    if first_share is None or second_share is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid share names provided.",
        )

    state["additive_share"] = (first_share + second_share) % state.get("p", 0)

    return {"result": "Additive share calculated successfully."}


@router.put(
    "/set-additive-share/{share_name}",
    status_code=status.HTTP_201_CREATED,
    summary="Set share from additive share",
    response_description="Share set from additive share.",
    response_model=ResultResponse,
    responses={
        201: {
            "description": "Share set from additive share.",
            "content": {
                "application/json": {
                    "example": {"result": "Share {share_name} set from additive share."}
                }
            },
        },
        400: {
            "description": "Additive share is not initialized.",
            "content": {
                "application/json": {
                    "example": {"detail": "additive_share is not initialized."}
                }
            },
        },
        403: {
            "description": "Forbidden. Only admin users can set this share.",
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
async def set_share_from_additive_share(
    share_name: str, current_user: dict = Depends(get_current_user)
):
    """
    Sets the share named {share_name} using the previously calculated additive share.

    Path Parameters:
    - `share_name`: The name of the share to set
    """
    if current_user.get("isAdmin") == False:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access this resource.",
        )

    validate_initialized(["additive_share"])

    state["shares"][share_name] = state.get("additive_share", 0)

    return {"result": f"Share {share_name} set from additive share."}

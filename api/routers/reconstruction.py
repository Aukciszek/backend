import asyncio
from random import sample
from typing import Annotated, Optional

import aiohttp
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status

from api.config import TRUSTED_IPS, state
from api.dependecies.auth import get_current_user
from api.models.parsers import ReconstructSecret, ReturnCalculatedShare, TokenData
from api.utils.utils import (
    computate_coefficients,
    reconstruct_secret,
    send_get_request,
    validate_initialized,
    validate_initialized_shares,
)

router = APIRouter(
    prefix="/api",
    tags=["Reconstruction"],
)


@router.get(
    "/return-share-to-reconstruct/{share_to_reconstruct}",
    status_code=status.HTTP_200_OK,
    summary="Return the share to reconstruct",
    response_description="Returns the party identifier along with the share to reconstruct (in hexadecimal).",
    response_model=ReturnCalculatedShare,
    responses={
        200: {
            "description": "Share to reconstruct returned successfully.",
            "content": {
                "application/json": {
                    "example": {"id": 1, "share_to_reconstruct": "0x123abc456def"}
                }
            },
        },
        400: {
            "description": "Invalid configuration.",
            "content": {
                "application/json": {
                    "example": {"detail": "Invalid TRUSTED_IPS configuration."}
                }
            },
        },
        403: {
            "description": "Forbidden. Request not from trusted IP.",
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
async def get_share_to_reconstruct(
    share_to_reconstruct: str,
    request: Request,
    X_Forwarded_For: Optional[str] = Header(None),
):
    """
    Returns the share for reconstruction associated with the requested share key.

    Path Parameters:
    - share_to_reconstruct: The share key to retrieve the associated share.
    """
    if not isinstance(TRUSTED_IPS, (list, tuple)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid TRUSTED_IPS configuration.",
        )

    if X_Forwarded_For:
        forwarded_ip = X_Forwarded_For.split(":")[0]
        if forwarded_ip not in TRUSTED_IPS:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to access this resource.",
            )
    elif not request.client or request.client.host not in TRUSTED_IPS:
        # If no X-Forwarded-For header is present, check the direct client IP
        # This is useful for cases where the request is not behind a proxy
        # and the client IP is directly accessible.
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access this resource.",
        )

    validate_initialized(["id"])
    validate_initialized_shares([share_to_reconstruct])

    return {
        "id": state.get("id", None),
        "share_to_reconstruct": hex(
            state.get("shares", {}).get(share_to_reconstruct, 0)
        ),
    }


@router.get(
    "/reconstruct-secret/{share_to_reconstruct}",
    status_code=status.HTTP_200_OK,
    summary="Reconstruct the secret",
    response_description="Reconstructed secret returned as hexadecimal string.",
    response_model=ReconstructSecret,
    responses={
        200: {
            "description": "Secret reconstructed successfully.",
            "content": {"application/json": {"example": {"secret": "0x123abc456def"}}},
        },
        400: {
            "description": "Server is not initialized.",
            "content": {
                "application/json": {"example": {"detail": "n is not initialized."}}
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
async def return_secret(
    share_to_reconstruct: str,
    current_user: Annotated[TokenData, Depends(get_current_user)],
):
    """
    Reconstructs the secret from the available calculated shares.

    Path Parameters:
    - share_to_reconstruct: The share key to reconstruct the secret from.
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access this resource.",
        )

    validate_initialized(["parties", "id", "t", "p"])
    validate_initialized_shares([share_to_reconstruct])

    parties = [
        party
        for i, party in enumerate(state.get("parties", []))
        if i != state.get("id", 0) - 1
    ]
    selected_parties = sample(parties, state.get("t", 0) - 1)

    async with aiohttp.ClientSession() as session:
        calculated_shares = []
        tasks = []
        for party in selected_parties:
            url = f"{party}/api/return-share-to-reconstruct/{share_to_reconstruct}"
            tasks.append(send_get_request(session, url))

        results = await asyncio.gather(*tasks)

        for result in results:
            calculated_shares.append(
                (result.get("id"), int(result.get("share_to_reconstruct"), 16))
            )

        calculated_shares.append(
            (
                state.get("id", None),
                state.get("shares", {}).get(share_to_reconstruct, 0),
            )
        )

        coefficients = computate_coefficients(calculated_shares, state.get("p", 0))

        secret = reconstruct_secret(calculated_shares, coefficients, state.get("p", 0))

        return {"secret": hex(secret % state.get("p", 0))}

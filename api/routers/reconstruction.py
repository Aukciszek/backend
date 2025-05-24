import asyncio
from random import sample

import aiohttp
from fastapi import APIRouter, Depends, HTTPException, Request, status

from api.config import TRUSTED_IPS, state
from api.dependecies.auth import get_current_user
from api.models.parsers import (
    ReconstructSecret,
    ReturnCalculatedShare,
    ShareToReconstruct,
)
from api.utils.utils import (
    computate_coefficients,
    reconstruct_secret,
    send_get_request,
    send_post_request,
    validate_initialized,
    validate_initialized_shares,
)

router = APIRouter(
    prefix="/api",
    tags=["Reconstruction"],
)


@router.get(
    "/return-calculated-share",
    status_code=status.HTTP_200_OK,
    summary="Return the calculated share",
    response_description="Returns the party identifier along with the calculated share (in hexadecimal).",
    response_model=ReturnCalculatedShare,
    responses={
        200: {
            "description": "Calculated share returned successfully.",
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
async def get_calculated_share(values: ShareToReconstruct, request: Request):
    """
    Returns the calculated share associated with the requested share key.
    """
    if not isinstance(TRUSTED_IPS, (list, tuple)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid TRUSTED_IPS configuration.",
        )

    if not request.client or request.client.host not in TRUSTED_IPS:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access this resource.",
        )

    validate_initialized(["id"])
    validate_initialized_shares([values.share_to_reconstruct])

    return {
        "id": state.get("id"),
        "share_to_reconstruct": hex(
            state.get("shares", {}).get(values.share_to_reconstruct, 0)
        ),
    }


@router.get(
    "/reconstruct-secret",
    status_code=status.HTTP_201_CREATED,
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
    values: ShareToReconstruct, current_user: dict = Depends(get_current_user)
):
    """
    Reconstructs the secret from the available calculated shares.
    """
    if current_user.get("isAdmin") == False:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access this resource.",
        )

    validate_initialized(["parties", "id", "t", "p"])
    validate_initialized_shares([values.share_to_reconstruct])

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
            url = f"{party}/api/return-calculated-share"
            json_data = {
                "share_to_reconstruct": values.share_to_reconstruct,
            }
            tasks.append(send_get_request(session, url, json_data))

        results = await asyncio.gather(*tasks)

        for result in results:
            calculated_shares.append(
                (result.get("id"), int(result.get("share_to_reconstruct"), 16))
            )

        calculated_shares.append(
            (
                state.get("id"),
                state.get("shares", {}).get(values.share_to_reconstruct, 0),
            )
        )

        coefficients = computate_coefficients(calculated_shares, state.get("p"))

        secret = reconstruct_secret(calculated_shares, coefficients, state.get("p"))

        return {"secret": hex(secret % state.get("p", 0))}

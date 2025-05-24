import asyncio
from random import sample

import aiohttp
from fastapi import APIRouter, Depends, HTTPException, Request, status

from api.config import TRUSTED_IPS, state
from api.dependecies.auth import get_current_user
from api.models.parsers import (
    CalculatedShareResponse,
    ReconstructedSecretResponse,
    ShareToReconstruct,
)
from api.utils.utils import (
    computate_coefficients,
    reconstruct_secret,
    send_post_request,
    validate_initialized,
    validate_initialized_shares,
)

router = APIRouter(
    prefix="/api",
    tags=["Reconstruction"],
)


@router.post(
    "/return-calculated-share",
    status_code=status.HTTP_201_CREATED,
    summary="Return the calculated share",
    response_description="Returns the calculated share.",
    responses={
        200: {
            "description": "Calculated share returned.",
            "content": {
                "application/json": {
                    "example": {"id": 1, "calculated_share": "0x123abc456def"}
                }
            },
        },
        400: {
            "description": "Invalid configuration.",
            "content": {
                "application/json": {
                    "examples": {
                        "invalid_config": {
                            "value": {"detail": "Invalid TRUSTED_IPS configuration."},
                            "summary": "Invalid configuration",
                        },
                        "missing_data": {
                            "value": {
                                "detail": "Calculated share or ID not initialized."
                            },
                            "summary": "Missing data",
                        },
                    }
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
    Returns the calculated share.
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


@router.post(
    "/reconstruct-secret",
    status_code=status.HTTP_201_CREATED,
    summary="Reconstruct the secret",
    response_description="Returns the reconstructed secret.",
    responses={
        200: {
            "description": "Secret reconstructed successfully.",
            "content": {"application/json": {"example": {"secret": "0x123abc456def"}}},
        },
        400: {
            "description": "Invalid state or configuration.",
            "content": {
                "application/json": {
                    "example": {"detail": "Server must be in share calculated state."}
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
async def return_secret(
    values: ShareToReconstruct, current_user: dict = Depends(get_current_user)
):
    """
    Reconstructs the secret from the shared values.
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
            tasks.append(send_post_request(session, url, json_data))

        results = await asyncio.gather(*tasks, return_exceptions=False)

        print(results)

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

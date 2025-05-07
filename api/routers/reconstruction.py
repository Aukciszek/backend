import asyncio
from random import sample

import aiohttp
from fastapi import APIRouter, HTTPException, status

from api.config import STATUS, state
from api.models.parsers import CalculatedShareResponse, ReconstructedSecretResponse
from api.utils.utils import (
    computate_coefficients,
    reconstruct_secret,
    send_get_request,
    validate_initialized,
)

router = APIRouter(
    prefix="/api",
    tags=["Reconstruction"],
)


@router.get(
    "/return-calculated-share",
    status_code=status.HTTP_200_OK,
    summary="Return the calculated share",
    response_description="Returns the calculated share.",
    response_model=CalculatedShareResponse,
    responses={
        200: {
            "description": "Calculated share returned.",
            "content": {
                "application/json": {
                    "example": {"id": 1, "calculated_share": "0x123456"}
                }
            },
        }
    },
)
async def get_calculated_share():
    """
    Returns the calculated share.
    """
    validate_initialized(["calculated_share", "id"])

    return {"id": state["id"], "calculated_share": hex(state["calculated_share"])}


@router.get(
    "/reconstruct-secret",
    status_code=status.HTTP_200_OK,
    summary="Reconstruct the secret",
    response_description="Returns the reconstructed secret.",
    response_model=ReconstructedSecretResponse,
    responses={
        200: {
            "description": "Secret reconstructed.",
            "content": {"application/json": {"example": {"secret": "0x123456"}}},
        }
    },
)
async def return_secret():
    """
    Reconstructs the secret from the shared values.
    """
    if state["status"] != STATUS.SHARE_CALCULATED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Server must be in share calculated state.",
        )

    validate_initialized(["calculated_share", "parties", "id", "t", "p"])

    parties = [
        party for i, party in enumerate(state["parties"]) if i != state["id"] - 1
    ]
    selected_parties = sample(parties, state["t"] - 1)

    async with aiohttp.ClientSession() as session:
        calculated_shares = []
        tasks = []
        for party in selected_parties:
            url = f"{party}/api/return-calculated-share"
            tasks.append(send_get_request(session, url))

        results = await asyncio.gather(*tasks)

        for result in results:
            calculated_shares.append(
                (result["id"], int(result["calculated_share"], 16))
            )

        calculated_shares.append((state["id"], state["calculated_share"]))

        coefficients = computate_coefficients(calculated_shares, state["p"])

        secret = reconstruct_secret(calculated_shares, coefficients, state["p"])

        return {"secret": hex(secret % state["p"])}

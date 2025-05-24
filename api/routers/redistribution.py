import asyncio

import aiohttp
from fastapi import APIRouter, Depends, HTTPException, Request, status

from api.config import TRUSTED_IPS, state
from api.dependecies.auth import get_current_user
from api.models.parsers import RData, ResultResponse, SharedQData, SharedRData
from api.utils.utils import (
    Shamir,
    send_post_request,
    validate_initialized,
    validate_initialized_shares,
    validate_initialized_shares_array,
)

router = APIRouter(
    prefix="/api",
    tags=["Redistribution"],
)


@router.post(
    "/redistribute-q",
    status_code=status.HTTP_201_CREATED,
    summary="Redistribute the 'q' shares among parties",
    response_description="'q' shares have been calculated and distributed.",
    response_model=ResultResponse,
    responses={
        201: {
            "description": "'q' calculated and shared successfully.",
            "content": {
                "application/json": {"example": {"result": "q calculated and shared"}}
            },
        },
        400: {
            "description": "Invalid server state.",
            "content": {
                "application/json": {
                    "example": {"detail": "Server must be in initialized state."}
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
async def redistribute_q(current_user: dict = Depends(get_current_user)):
    """
    Calculates and distributes the 'q' shares to all participating parties.
    """
    if current_user.get("isAdmin") == False:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access this resource.",
        )

    validate_initialized(["t", "n", "p", "id", "parties"])
    validate_initialized_shares(["shared_q"])

    q = Shamir(2 * state.get("t", 0), state.get("n", 0), 0, state.get("p", 0))

    async with aiohttp.ClientSession() as session:
        tasks = []
        for i in range(state.get("n", 0)):
            if i == state.get("id", 0) - 1:
                state["shares"]["shared_q"][i] = q[i][1]
                continue

            url = f"{state['parties'][i]}/api/receive-q-from-parties"
            json_data = {"party_id": state.get("id"), "shared_q": hex(q[i][1])}
            tasks.append(send_post_request(session, url, json_data))

        await asyncio.gather(*tasks)

        return {"result": "q calculated and shared"}


@router.post(
    "/receive-q-from-parties",
    status_code=status.HTTP_201_CREATED,
    summary="Receive 'q' share from another party",
    response_description="'q' share has been received and stored.",
    response_model=ResultResponse,
    responses={
        201: {
            "description": "'q' received successfully.",
            "content": {"application/json": {"example": {"result": "q received"}}},
        },
        400: {
            "description": "Invalid request.",
            "content": {
                "application/json": {
                    "examples": {
                        "invalid_party": {
                            "value": {"detail": "Invalid party id."},
                            "summary": "Invalid party ID",
                        },
                        "already_set": {
                            "value": {"detail": "q is already set from this party."},
                            "summary": "Already set",
                        },
                        "invalid_config": {
                            "value": {"detail": "Invalid TRUSTED_IPS configuration."},
                            "summary": "Invalid configuration",
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
async def set_received_q(values: SharedQData, request: Request):
    """
    Receives and stores a 'q' share from another participating party.

    Request Body:
     - `party_id`: id of the party sending the share
     - `shared_q`: the q share (hexadecimal string)
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

    # if TRUSTED_IPS.index(request.client.host) != values.party_id - 1:
    #     raise HTTPException(
    #         status_code=status.HTTP_403_FORBIDDEN,
    #         detail="You do not have permission to access this resource.",
    #     ) TODO:

    validate_initialized_shares(["shared_q"])

    if (
        values.party_id > len(state.get("shares", {}).get("shared_q", []))
        or values.party_id < 1
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid party id."
        )

    if state.get("shares", {}).get("shared_q", [])[values.party_id - 1] is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="q is already set from this party.",
        )

    state["shares"]["shared_q"][values.party_id - 1] = int(values.shared_q, 16)

    return {"result": "q received"}


@router.post(
    "/redistribute-r",
    status_code=status.HTTP_201_CREATED,
    summary="Redistribute the 'r' shares among parties",
    response_description="'r' shares have been calculated and distributed.",
    response_model=ResultResponse,
    responses={
        201: {
            "description": "'r' calculated and shared successfully.",
            "content": {
                "application/json": {"example": {"result": "r calculated and shared"}}
            },
        },
        400: {
            "description": "Invalid server state or parameters.",
            "content": {
                "application/json": {
                    "examples": {
                        "invalid_state": {
                            "value": {
                                "detail": "Server must be in q calculated and shared state."
                            },
                            "summary": "Invalid state",
                        },
                        "missing_params": {
                            "value": {
                                "detail": "opened_a must be provided when calculate_final_comparison_result is True."
                            },
                            "summary": "Missing parameter",
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
async def redistribute_r(values: RData, current_user: dict = Depends(get_current_user)):
    """
    Calculates and distributes the 'r' shares to all participating parties, based on previously distributed 'q' shares.

    Request Body:
    - `first_share_name`: name of the first share
    - `second_share_name`: name of the second share
    """
    if current_user.get("isAdmin") == False:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access this resource.",
        )

    # Validate required state variables
    validate_initialized(["n", "p", "t", "id", "parties", "A"])
    validate_initialized_shares(["shared_r"])
    validate_initialized_shares_array(["shared_q"])

    first_share = state.get("shares", {}).get(values.first_share_name, None)
    second_share = state.get("shares", {}).get(values.second_share_name, None)

    if first_share is None or second_share is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid share names provided.",
        )

    qs = [x for x in state.get("shares", {}).get("shared_q", []) if x is not None]

    multiplied_shares = ((first_share * second_share) + sum(qs)) % state.get("p", 0)

    r = [
        (multiplied_shares * state.get("A", 0)[state.get("id", 0) - 1][i])
        % state.get("p")
        for i in range(state.get("n", 0))
    ]

    # Distribute r values to other parties
    async with aiohttp.ClientSession() as session:
        tasks = []
        for i in range(state.get("n", 0)):
            if i == state.get("id", 0) - 1:
                state["shares"]["shared_r"][i] = r[i]
                continue

            url = f"{state['parties'][i]}/api/receive-r-from-parties"
            json_data = {"party_id": state.get("id"), "shared_r": hex(r[i])}
            tasks.append(send_post_request(session, url, json_data))

        await asyncio.gather(*tasks, return_exceptions=False)

        return {"result": "r calculated and shared"}


@router.post(
    "/receive-r-from-parties",
    status_code=status.HTTP_201_CREATED,
    summary="Receive 'r' share from another party",
    response_description="'r' share has been received.",
    response_model=ResultResponse,
    responses={
        201: {
            "description": "'r' received successfully.",
            "content": {"application/json": {"example": {"result": "r received"}}},
        },
        400: {
            "description": "Invalid request.",
            "content": {
                "application/json": {
                    "examples": {
                        "invalid_party": {
                            "value": {"detail": "Invalid party id."},
                            "summary": "Invalid party ID",
                        },
                        "already_set": {
                            "value": {"detail": "r is already set from this party."},
                            "summary": "Already set",
                        },
                        "invalid_config": {
                            "value": {"detail": "Invalid TRUSTED_IPS configuration."},
                            "summary": "Invalid configuration",
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
async def set_received_r(values: SharedRData, request: Request):
    """
    Receives and stores an 'r' share from another participating party.

    Request Body:
    - `party_id`: id of the party sending the share
    - `shared_r`: the r share (hexadecimal string)
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

    # if TRUSTED_IPS.index(request.client.host) != values.party_id - 1:
    #     raise HTTPException(
    #         status_code=status.HTTP_403_FORBIDDEN,
    #         detail="You do not have permission to access this resource.",
    #     ) TODO:

    if (
        values.party_id > len(state.get("shares", {}).get("shared_r", []))
        or values.party_id < 1
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid party id."
        )

    if state.get("shares", {}).get("shared_r", [])[values.party_id - 1] is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="r is already set from this party.",
        )

    state["shares"]["shared_r"][values.party_id - 1] = int(values.shared_r, 16)

    return {"result": "r received"}

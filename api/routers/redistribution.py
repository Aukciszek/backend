import asyncio
from typing import Annotated, Optional

import aiohttp
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status

from api.config import TRUSTED_IPS, USING_WIREGUARD, state
from api.dependecies.auth import get_current_user
from api.models.parsers import (
    RData,
    ResultResponse,
    SharedQData,
    SharedRData,
    SharedUData,
    TokenData,
)
from api.routers.reconstruction import request_is_from_trusted_ip
from api.utils.utils import (
    Shamir,
    secure_randint,
    send_post_request,
    validate_initialized,
    validate_initialized_shares,
    validate_initialized_shares_array,
)

router = APIRouter(
    prefix="/api",
    tags=["Redistribution"],
)


@router.put(
    "/redistribute-q",
    status_code=status.HTTP_201_CREATED,
    summary="Redistribute 'q' shares among parties",
    response_description="'q' shares (hexadecimal) computed with Shamir's scheme are distributed to all parties.",
    response_model=ResultResponse,
    responses={
        201: {
            "description": "'q' calculated and shared successfully.",
            "content": {
                "application/json": {"example": {"result": "q calculated and shared"}}
            },
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
async def redistribute_q(current_user: Annotated[TokenData, Depends(get_current_user)]):
    """
    Computes 'q' shares using a Shamir scheme and distributes them to all participating parties.
    """
    if not current_user.is_admin:
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
            json_data = {"party_id": state.get("id", None), "shared_q": hex(q[i][1])}
            tasks.append(send_post_request(session, url, json_data))

        await asyncio.gather(*tasks)

        return {"result": "q calculated and shared"}


@router.post(
    "/receive-q-from-parties",
    status_code=status.HTTP_201_CREATED,
    summary="Receive 'q' share from a party",
    response_description="'q' share received (as hexadecimal) and stored.",
    response_model=ResultResponse,
    responses={
        201: {
            "description": "'q' share received successfully.",
            "content": {"application/json": {"example": {"result": "q received"}}},
        },
        400: {
            "description": "Invalid request.",
            "content": {
                "application/json": {
                    "examples": {
                        "invalid_party": {
                            "value": {"detail": "Invalid party id."},
                        },
                        "already_set": {
                            "value": {"detail": "q is already set from this party."},
                        },
                        "invalid_config": {
                            "value": {"detail": "Invalid TRUSTED_IPS configuration."},
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
async def set_received_q(
    values: SharedQData, request: Request, X_Forwarded_For: Optional[str] = Header(None)
):
    """
    Receives a 'q' share from another party and stores it.

    Request Body:
    - `party_id`: The ID of the party sending the share
    - `shared_q`: The q share value (hexadecimal string)

    Dependencies:
    - `request`: HTTP request object for IP validation
    """
    if not request_is_from_trusted_ip(request,X_Forwarded_For):
        raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to access this resource.",
            )

    # if X_Forwarded_For:
    #     forwarded_ip = X_Forwarded_For.split(":")[0]
    #     if TRUSTED_IPS.index(forwarded_ip) != values.party_id - 1:
    #         raise HTTPException(
    #             status_code=status.HTTP_403_FORBIDDEN,
    #             detail="You do not have permission to access this resource.",
    #         )
    # elif request.client and request.client.host:
    #     if TRUSTED_IPS.index(request.client.host) != values.party_id - 1:
    #         raise HTTPException(
    #             status_code=status.HTTP_403_FORBIDDEN,
    #             detail="You do not have permission to access this resource.",
    #         )
    # else:
    #     raise HTTPException(
    #         status_code=status.HTTP_403_FORBIDDEN,
    #         detail="You do not have permission to access this resource.",
    #     )
    # TODO: When deploying, uncomment this line
    # to ensure that only the party with the correct IP can set the value

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


@router.put(
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
                    "example": {"detail": "Invalid share names provided."}
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
async def redistribute_r(
    values: RData, current_user: Annotated[TokenData, Depends(get_current_user)]
):
    """
    Calculates and distributes the 'r' shares to all participating parties, based on previously distributed 'q' shares.

    Request Body:
    - `first_share_name`: name of the first share
    - `second_share_name`: name of the second share
    """
    if not current_user.is_admin:
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

    qs = [x for x in state.get("shares", {}).get("shared_q", [])]

    multiplied_shares = ((first_share * second_share) + sum(qs)) % state.get("p", 0)

    r = [
        (multiplied_shares * state.get("A", 0)[state.get("id", 0) - 1][i])
        % state.get("p", 0)
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
            json_data = {"party_id": state.get("id", None), "shared_r": hex(r[i])}
            tasks.append(send_post_request(session, url, json_data))

        await asyncio.gather(*tasks)

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
                        },
                        "already_set": {
                            "value": {"detail": "r is already set from this party."},
                        },
                        "invalid_config": {
                            "value": {"detail": "Invalid TRUSTED_IPS configuration."},
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
async def set_received_r(
    values: SharedRData, request: Request, X_Forwarded_For: Optional[str] = Header(None)
):
    """
    Receives and stores an 'r' share from another participating party.

    Request Body:
    - `party_id`: The ID of the party sending the share
    - `shared_r`: The r share value (hexadecimal string)

    Dependencies:
    - `request`: HTTP request object for IP validation
    """
    if not request_is_from_trusted_ip(request,X_Forwarded_For):
        raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to access this resource.",
            )

    # if X_Forwarded_For:
    #     forwarded_ip = X_Forwarded_For.split(":")[0]
    #     if TRUSTED_IPS.index(forwarded_ip) != values.party_id - 1:
    #         raise HTTPException(
    #             status_code=status.HTTP_403_FORBIDDEN,
    #             detail="You do not have permission to access this resource.",
    #         )
    # elif request.client and request.client.host:
    #     if TRUSTED_IPS.index(request.client.host) != values.party_id - 1:
    #         raise HTTPException(
    #             status_code=status.HTTP_403_FORBIDDEN,
    #             detail="You do not have permission to access this resource.",
    #         )
    # else:
    #     raise HTTPException(
    #         status_code=status.HTTP_403_FORBIDDEN,
    #         detail="You do not have permission to access this resource.",
    #     ) TODO: When deploying, uncomment this line
    # to ensure that only the party with the correct IP can set the value

    validate_initialized_shares(["shared_r"])

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


@router.put(
    "/redistribute-u",
    status_code=status.HTTP_201_CREATED,
    summary="Redistribute the 'u' shares among parties",
    response_description="'u' shares have been calculated and distributed.",
    response_model=ResultResponse,
    responses={
        201: {
            "description": "'u' calculated and shared successfully.",
            "content": {
                "application/json": {"example": {"result": "u calculated and shared"}}
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
async def redistribute_u(current_user: Annotated[TokenData, Depends(get_current_user)]):
    """
    Calculates and distributes the 'u' shares to all participating parties.
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access this resource.",
        )

    validate_initialized(["t", "n", "p", "id", "parties"])
    validate_initialized_shares(["shared_u"])

    u = Shamir(
        state.get("t", 0),
        state.get("n", 0),
        secure_randint(1, state.get("p", 0)),
        state.get("p", 0),
    )

    async with aiohttp.ClientSession() as session:
        tasks = []
        for i in range(state.get("n", 0)):
            if i == state.get("id", 0) - 1:
                state["shares"]["shared_u"][i] = u[i][1]
                continue

            url = f"{state['parties'][i]}/api/receive-u-from-parties"
            json_data = {"party_id": state.get("id", None), "shared_u": hex(u[i][1])}
            tasks.append(send_post_request(session, url, json_data))

        await asyncio.gather(*tasks)

        return {"result": "u calculated and shared"}


@router.post(
    "/receive-u-from-parties",
    status_code=status.HTTP_201_CREATED,
    summary="Receive 'u' share from another party",
    response_description="'u' share has been received and stored.",
    response_model=ResultResponse,
    responses={
        201: {
            "description": "'u' received successfully.",
            "content": {"application/json": {"example": {"result": "u received"}}},
        },
        400: {
            "description": "Invalid request.",
            "content": {
                "application/json": {
                    "examples": {
                        "invalid_party": {
                            "value": {"detail": "Invalid party id."},
                        },
                        "already_set": {
                            "value": {"detail": "u is already set from this party."},
                        },
                        "invalid_config": {
                            "value": {"detail": "Invalid TRUSTED_IPS configuration."},
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
async def receive_u_from_parties(
    values: SharedUData, request: Request, X_Forwarded_For: Optional[str] = Header(None)
):
    """
    Receives a 'u' share from another party and stores it.

    Request Body:
    - `party_id`: The ID of the party sending the share
    - `shared_u`: The u share value (hexadecimal string)

    Dependencies:
    - `request`: HTTP request object for IP validation
    """
    if not request_is_from_trusted_ip(request,X_Forwarded_For):
        raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to access this resource.",
            )

    # if X_Forwarded_For:
    #     forwarded_ip = X_Forwarded_For.split(":")[0]
    #     if TRUSTED_IPS.index(forwarded_ip) != values.party_id - 1:
    #         raise HTTPException(
    #             status_code=status.HTTP_403_FORBIDDEN,
    #             detail="You do not have permission to access this resource.",
    #         )
    # elif request.client and request.client.host:
    #     if TRUSTED_IPS.index(request.client.host) != values.party_id - 1:
    #         raise HTTPException(
    #             status_code=status.HTTP_403_FORBIDDEN,
    #             detail="You do not have permission to access this resource.",
    #         )
    # else:
    #     raise HTTPException(
    #         status_code=status.HTTP_403_FORBIDDEN,
    #         detail="You do not have permission to access this resource.",
    #     ) TODO: When deploying, uncomment this line
    # to ensure that only the party with the correct IP can set the value

    validate_initialized_shares(["shared_u"])

    if (
        values.party_id > len(state.get("shares", {}).get("shared_u", []))
        or values.party_id < 1
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid party id."
        )

    state["shares"]["shared_u"][values.party_id - 1] = int(values.shared_u, 16)

    return {"result": "u received"}


@router.put(
    "/calculate-shared-u",
    status_code=status.HTTP_201_CREATED,
    summary="Calculate shared 'u' value",
    response_description="'u' value has been calculated.",
    response_model=ResultResponse,
    responses={
        201: {
            "description": "'u' calculated successfully.",
            "content": {
                "application/json": {
                    "example": {"result": "Shared u calculated successfully."}
                }
            },
        },
        400: {
            "description": "Server is not initialized.",
            "content": {
                "application/json": {"example": {"detail": "p is not initialized."}}
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
async def calculate_u(current_user: Annotated[TokenData, Depends(get_current_user)]):
    """
    Calculates the shared 'u' value from distributed 'u' shares.
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access this resource.",
        )

    validate_initialized(["p"])
    validate_initialized_shares_array(["shared_u"])

    state["shares"]["u"] = sum(state.get("shares", {}).get("shared_u", [])) % state.get(
        "p", 0
    )

    return {"result": "Shared u calculated successfully."}

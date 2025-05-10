import asyncio

import aiohttp
from fastapi import APIRouter, Depends, HTTPException, Request, status

from api.config import STATUS, TRUSTED_IPS, state
from api.dependecies.auth import get_current_user
from api.models.parsers import RData, ResultResponse, SharedQData, SharedRData
from api.utils.utils import (
    Shamir,
    binary,
    binary_exponentiation,
    get_temporary_zZ,
    inverse_matrix_mod,
    multiply_matrix,
    send_post_request,
    validate_initialized,
    validate_initialized_array,
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

    if state.get("status") != STATUS.INITIALIZED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Server must be in initialized state.",
        )

    validate_initialized(["t", "n", "p", "id", "parties", "shared_q"])

    q = Shamir(2 * state.get("t", 0), state.get("n", 0), 0, state.get("p", 0))

    async with aiohttp.ClientSession() as session:
        tasks = []
        for i in range(state.get("n", 0)):
            if i == state.get("id", 0) - 1:
                state["shared_q"][i] = q[i][1]
                continue

            url = f"{state['parties'][i]}/api/receive-q-from-parties"
            json_data = {"party_id": state.get("id"), "shared_q": hex(q[i][1])}
            tasks.append(send_post_request(session, url, json_data))

        await asyncio.gather(*tasks)

        state.update({"status": STATUS.Q_CALC_SHARED})
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

    validate_initialized(["shared_q"])

    if values.party_id > len(state.get("shared_q", [])) or values.party_id < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid party id."
        )

    if state.get("shared_q", [])[values.party_id - 1] is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="q is already set from this party.",
        )

    state["shared_q"][values.party_id - 1] = int(values.shared_q, 16)

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
    - `take_value_from_temporary_zZ`: Flag indicating whether to take the second value from temporary_zZ
    - `zZ_first_multiplication_factor`: The first multiplication factor from zZ
    - `zZ_second_multiplication_factor`: The second multiplication factor from zZ
    - `calculate_final_comparison_result`: Flag indicating whether to calculate the final comparison result
    - `opened_a`: Opened value of a (hexadecimal string)
    - `l`: length
    - `k`: kappa
    """
    if current_user.get("isAdmin") == False:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access this resource.",
        )

    # Validate server state
    if state.get("status") != STATUS.Q_CALC_SHARED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Server must be in q calculated and shared state.",
        )

    # Validate required state variables
    validate_initialized(["client_shares", "n", "p", "t", "id", "shared_r", "parties"])
    validate_initialized_array(["shared_q"])

    # Check for optional parameters
    if values.calculate_final_comparison_result:
        if values.opened_a is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="opened_a must be provided when calculate_final_comparison_result is True.",
            )
        if values.l is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="l must be provided when calculate_final_comparison_result is True.",
            )
        if values.k is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="k must be provided when calculate_final_comparison_result is True.",
            )
    else:
        if values.zZ_first_multiplication_factor is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="zZ_first_multiplication_factor must be provided when calculate_final_comparison_result is False.",
            )
        if values.zZ_second_multiplication_factor is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="zZ_second_multiplication_factor must be provided when calculate_final_comparison_result is False.",
            )

    # Extract multiplication factors based on the condition
    first_multiplication_factor = 0
    second_multiplication_factor = 0

    if not values.calculate_final_comparison_result:
        first_multiplication_factor = state.get("zZ", [])[
            values.zZ_first_multiplication_factor[0]
        ][values.zZ_first_multiplication_factor[1]]

        if values.take_value_from_temporary_zZ:
            second_multiplication_factor = get_temporary_zZ(
                values.zZ_second_multiplication_factor[0]
            )
        else:
            second_multiplication_factor = state.get("zZ", [])[
                values.zZ_second_multiplication_factor[0]
            ][values.zZ_second_multiplication_factor[1]]

    # Generate matrix B
    B = [list(range(1, state.get("n", 0) + 1)) for _ in range(state.get("n", 0))]
    for j in range(state.get("n", 0)):
        for k in range(state.get("n", 0)):
            B[j][k] = binary_exponentiation(B[j][k], j, state.get("p"))

    # Compute inverse of B
    B_inv = inverse_matrix_mod(B, state.get("p"))

    # Generate matrix P
    P = [[0] * state.get("n", 0) for _ in range(state.get("n", 0))]
    for i in range(state.get("t", 0)):
        P[i][i] = 1

    # Compute matrix A
    A = multiply_matrix(multiply_matrix(B_inv, P, state.get("p")), B, state.get("p"))

    # Compute multiplied shares
    multiplied_shares = 0
    if values.calculate_final_comparison_result:
        a_bin = binary(int(values.opened_a, 16))

        while len(a_bin) < values.l + values.k + 2:
            a_bin.append(0)

        multiplied_shares = (
            a_bin[values.l] * state.get("zZ", [])[0][1] + sum(state.get("shared_q", []))
        ) % state.get("p")
    else:
        multiplied_shares = (
            first_multiplication_factor * second_multiplication_factor
            + sum(state.get("shared_q", []))
        ) % state.get("p", 0)

    # Compute r values
    r = [
        (multiplied_shares * A[state.get("id", 0) - 1][i]) % state.get("p")
        for i in range(state.get("n", 0))
    ]

    # Distribute r values to other parties
    async with aiohttp.ClientSession() as session:
        tasks = []
        for i in range(state.get("n", 0)):
            if i == state.get("id", 0) - 1:
                state["shared_r"][i] = r[i]
                continue

            url = f"{state['parties'][i]}/api/receive-r-from-parties"
            json_data = {"party_id": state.get("id"), "shared_r": hex(r[i])}
            tasks.append(send_post_request(session, url, json_data))

        await asyncio.gather(*tasks)

        # Update state and return response
        state.update({"status": STATUS.R_CALC_SHARED})
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

    validate_initialized(["shared_r"])

    if values.party_id > len(state.get("shared_r", [])) or values.party_id < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid party id."
        )

    if state.get("shared_r", [])[values.party_id - 1] is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="r is already set from this party.",
        )

    state["shared_r"][values.party_id - 1] = int(values.shared_r, 16)

    return {"result": "r received"}

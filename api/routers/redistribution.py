import asyncio

import aiohttp
from fastapi import APIRouter, HTTPException, status

from api.config import STATUS, state
from api.models.parsers import RData, SharedQData, SharedRData
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
    responses={
        201: {
            "description": "'q' calculated and shared.",
            "content": {
                "application/json": {"example": {"result": "q calculated and shared"}}
            },
        },
        400: {
            "description": "Server must be initialized.",
            "content": {
                "application/json": {
                    "example": {"detail": "Server must be in initialized state."}
                }
            },
        },
    },
)
async def redistribute_q():
    """
    Calculates and distributes the 'q' shares to all participating parties.
    """
    if state["status"] != STATUS.INITIALIZED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Server must be in initialized state.",
        )

    validate_initialized(["t", "n", "p", "id", "parties", "shared_q"])

    q = Shamir(2 * state["t"], state["n"], 0, state["p"])

    async with aiohttp.ClientSession() as session:
        tasks = []
        for i in range(state["n"]):
            if i == state["id"] - 1:
                state["shared_q"][i] = q[i][1]
                continue

            url = f"{state['parties'][i]}/api/receive-q-from-parties"
            json_data = {"party_id": state["id"], "shared_q": hex(q[i][1])}
            tasks.append(send_post_request(session, url, json_data))

        await asyncio.gather(*tasks)

        state["status"] = STATUS.Q_CALC_SHARED
        return {"result": "q calculated and shared"}


@router.post(
    "/receive-q-from-parties",
    status_code=status.HTTP_201_CREATED,
    summary="Receive 'q' share from another party",
    response_description="'q' share has been received and stored.",
    responses={
        201: {
            "description": "'q' received.",
            "content": {"application/json": {"example": {"result": "q received"}}},
        },
        400: {
            "description": "Invalid party ID or 'q' already set.",
            "content": {
                "application/json": {"example": {"detail": "Invalid party id."}}
            },
        },
    },
)
async def set_received_q(values: SharedQData):
    """
    Receives and stores a 'q' share from another participating party.

    Request Body:
     - `party_id`: id of the party sending the share
     - `shared_q`: the q share (hexadecimal string)
    """
    validate_initialized(["shared_q"])

    if values.party_id > len(state["shared_q"]) or values.party_id < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid party id."
        )

    if state["shared_q"][values.party_id - 1] is not None:
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
    responses={
        201: {
            "description": "'r' calculated and shared.",
            "content": {
                "application/json": {"example": {"result": "r calculated and shared"}}
            },
        },
        400: {
            "description": "Server must be in 'q' calculated and shared state.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Server must be in q calculated and shared state."
                    }
                }
            },
        },
    },
)
async def redistribute_r(values: RData):
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
    # Validate server state
    if state["status"] != STATUS.Q_CALC_SHARED:
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
        first_multiplication_factor = state["zZ"][
            values.zZ_first_multiplication_factor[0]
        ][values.zZ_first_multiplication_factor[1]]

        if values.take_value_from_temporary_zZ:
            second_multiplication_factor = get_temporary_zZ(
                values.zZ_second_multiplication_factor[0]
            )
        else:
            second_multiplication_factor = state["zZ"][
                values.zZ_second_multiplication_factor[0]
            ][values.zZ_second_multiplication_factor[1]]

    # Generate matrix B
    B = [list(range(1, state["n"] + 1)) for _ in range(state["n"])]
    for j in range(state["n"]):
        for k in range(state["n"]):
            B[j][k] = binary_exponentiation(B[j][k], j, state["p"])

    # Compute inverse of B
    B_inv = inverse_matrix_mod(B, state["p"])

    # Generate matrix P
    P = [[0] * state["n"] for _ in range(state["n"])]
    for i in range(state["t"]):
        P[i][i] = 1

    # Compute matrix A
    A = multiply_matrix(multiply_matrix(B_inv, P, state["p"]), B, state["p"])

    # Compute multiplied shares
    multiplied_shares = 0
    if values.calculate_final_comparison_result:
        a_bin = binary(int(values.opened_a, 16))

        while len(a_bin) < values.l + values.k + 2:
            a_bin.append(0)

        multiplied_shares = (
            a_bin[values.l] * state["zZ"][0][1] + sum(state["shared_q"])
        ) % state["p"]
    else:
        multiplied_shares = (
            first_multiplication_factor * second_multiplication_factor
            + sum(state["shared_q"])
        ) % state["p"]

    # Compute r values
    r = [
        (multiplied_shares * A[state["id"] - 1][i]) % state["p"]
        for i in range(state["n"])
    ]

    # Distribute r values to other parties
    async with aiohttp.ClientSession() as session:
        tasks = []
        for i in range(state["n"]):
            if i == state["id"] - 1:
                state["shared_r"][i] = r[i]
                continue

            url = f"{state['parties'][i]}/api/receive-r-from-parties"
            json_data = {"party_id": state["id"], "shared_r": hex(r[i])}
            tasks.append(send_post_request(session, url, json_data))

        await asyncio.gather(*tasks)

        # Update state and return response
        state["status"] = STATUS.R_CALC_SHARED
        return {"result": "r calculated and shared"}


@router.post(
    "/receive-r-from-parties",
    status_code=status.HTTP_201_CREATED,
    summary="Receive 'r' share from another party",
    response_description="'r' share has been received.",
    responses={
        201: {
            "description": "'r' received.",
            "content": {"application/json": {"example": {"result": "r received"}}},
        },
        400: {
            "description": "Invalid party ID or 'r' already set.",
            "content": {
                "application/json": {"example": {"detail": "Invalid party id."}}
            },
        },
    },
)
async def set_received_r(values: SharedRData):
    """
    Receives and stores an 'r' share from another participating party.

    Request Body:
    - `party_id`: id of the party sending the share
    - `shared_r`: the r share (hexadecimal string)
    """
    validate_initialized(["shared_r"])

    if values.party_id > len(state["shared_r"]) or values.party_id < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid party id."
        )

    if state["shared_r"][values.party_id - 1] is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="r is already set from this party.",
        )

    state["shared_r"][values.party_id - 1] = int(values.shared_r, 16)

    return {"result": "r received"}

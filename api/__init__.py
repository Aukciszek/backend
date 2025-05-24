import asyncio
import random

import aiohttp
from fastapi import Depends, FastAPI, HTTPException, status
from starlette.middleware.cors import CORSMiddleware

from api.config import state
from api.dependecies.auth import get_current_user
from api.models.parsers import (
    AdditiveShareData,
    InitializezAndZZData,
    PrepareZTablesData,
    SetShareData,
    SharedUData,
)
from api.routers import (
    auth,
    bidders,
    comparison,
    initialization,
    multiplication,
    reconstruction,
    redistribution,
    reset,
    shares,
    xor,
)
from api.utils.utils import (
    Shamir,
    binary,
    binary_exponentiation,
    inverse_matrix_mod,
    multiply_matrix,
    send_post_request,
    validate_initialized,
    validate_not_initialized,
)

app = FastAPI(
    title="Secure Multi-Party Computation API",
    version="1.0.0",
    description="API for performing secure multi-party computation protocols.",
    openapi_tags=[
        {
            "name": "Status",
            "description": "Endpoints for checking the server status.",
        },
        {
            "name": "Initialization",
            "description": "Endpoints for setting up the initial parameters of the MPC protocol.",
        },
        {
            "name": "Shares",
            "description": "Endpoints for managing and setting client shares.",
        },
        {
            "name": "Comparison",
            "description": "Endpoints for performing secure comparison protocols.",
        },
        {
            "name": "Redistribution",
            "description": "Endpoints for redistributing intermediate values (q and r).",
        },
        {
            "name": "Multiplication",
            "description": "Endpoints for secure multiplication steps.",
        },
        {
            "name": "XOR",
            "description": "Endpoint for secure XOR operation.",
        },
        {
            "name": "Reconstruction",
            "description": "Endpoint for reconstructing the final secret or comparison result.",
        },
        {
            "name": "Reset",
            "description": "Endpoints for resetting the server state.",
        },
        {
            "name": "Authentication",
            "description": "Endpoints for user registration and login.",
        },
        {
            "name": "Bidders",
            "description": "Endpoints for retrieving information about bidders",
        },
    ],
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.put("/api/calculate-A", status_code=status.HTTP_201_CREATED)
async def calculate_A(current_user: dict = Depends(get_current_user)):
    validate_initialized(["t", "n", "p"])
    validate_not_initialized(["A"])

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
    state["A"] = multiply_matrix(
        multiply_matrix(B_inv, P, state.get("p")), B, state.get("p")
    )

    return {"result": "Matrix A calculated successfully."}


@app.post("/api/set-multiplicative-share/{share_name}")
async def set_share_from_multiplicative_share(
    share_name: str, current_user: dict = Depends(get_current_user)
):
    validate_initialized(["multiplicative_share", "shares"])

    state["shares"][share_name] = state["multiplicative_share"]

    return {"result": f"Share {share_name} set from multiplicative share."}


@app.post(
    "/api/redistribute-u",
)
async def redistribute_u(current_user: dict = Depends(get_current_user)):
    u = Shamir(state["t"], state["n"], random.randint(1, state["p"]), state["p"])

    async with aiohttp.ClientSession() as session:
        tasks = []
        for i in range(state.get("n", 0)):
            if i == state.get("id", 0) - 1:
                state["shares"]["shared_u"][i] = u[i][1]
                continue

            url = f"{state['parties'][i]}/api/receive-u-from-parties"
            json_data = {"party_id": state.get("id"), "shared_u": hex(u[i][1])}
            tasks.append(send_post_request(session, url, json_data))

        await asyncio.gather(*tasks)

        return {"result": "u calculated and shared"}


@app.post(
    "/api/receive-u-from-parties",
    status_code=status.HTTP_201_CREATED,
)
async def receive_u_from_parties(values: SharedUData):
    print(f"Received u from party {values.party_id}: {values.shared_u}")
    print(state.get("shares", {}).get("shared_u", []))

    if (
        values.party_id > len(state.get("shares", {}).get("shared_u", []))
        or values.party_id < 1
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid party id."
        )

    state["shares"]["shared_u"][values.party_id - 1] = int(values.shared_u, 16)

    return {"result": "u received"}


@app.post("/api/calculate-shared-u")
async def calculate_u(current_user: dict = Depends(get_current_user)):
    state["shares"]["u"] = sum(state.get("shares", {}).get("shared_u", [])) % state.get(
        "p", 0
    )

    return {"result": "Shared u calculated successfully."}


@app.post("/api/set-shares")
async def set_shares(
    values: SetShareData, current_user: dict = Depends(get_current_user)
):
    validate_initialized(["shares"])

    state["shares"][values.share_name] = int(values.share_value, 16)

    return {"result": f"Share {values.share_name} set successfully."}


@app.post("/api/calculate-additive-share")
async def calculate_additive_share(
    values: AdditiveShareData, current_user: dict = Depends(get_current_user)
):
    validate_initialized(["shares"])

    first_share = state.get("shares", {}).get(values.first_share_name, None)
    second_share = state.get("shares", {}).get(values.second_share_name, None)

    if first_share is None or second_share is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid share names provided.",
        )

    state["additive_share"] = (first_share + second_share) % state.get("p", 0)

    return {"result": "Additive share calculated successfully."}


@app.post("/api/set-addtive-share/{share_name}")
async def set_share_from_addtive_share(share_name: str):
    validate_initialized(["additive_share", "shares"])

    state["shares"][share_name] = state["additive_share"]

    return {"result": f"Share {share_name} set from additive share."}


@app.post("/api/set-xor-share/{share_name}")
async def set_share_from_xor_share(
    share_name: str, current_user: dict = Depends(get_current_user)
):
    validate_initialized(["xor_share", "shares"])

    state["shares"][share_name] = state["xor_share"]

    return {"result": f"Share {share_name} set from xor share."}


@app.post("/api/set-temporary-random-bit-share/{bit_index}")
async def set_random_number_bit_share_to_temporary_random_bit_share(
    bit_index: int, current_user: dict = Depends(get_current_user)
):
    while len(state.get("random_number_bit_shares", [])) < bit_index + 1:
        state["random_number_bit_shares"].append(None)

    state["random_number_bit_shares"][bit_index] = (
        state.get("id", 0),
        state.get("shares", {}).get("temporary_random_bit", None),
    )

    return {"result": f"Random number bit share at index {bit_index} set successfully."}


@app.post("/api/calculate-share-of-random-number")
async def calculate_share_of_random_number(
    current_user: dict = Depends(get_current_user),
):
    def multiply_bit_shares_by_powers_of_2(shares):
        multiplied_shares = []
        for i in range(len(shares)):
            multiplied_shares.append((shares[i][0], 2**i * shares[i][1]))
        return multiplied_shares

    def add_multiplied_shares(multiplied_shares):
        party_id = multiplied_shares[0][0]
        value_of_share_r = multiplied_shares[0][1]
        for i in range(1, len(multiplied_shares)):
            value_of_share_r += multiplied_shares[i][1]
        return (
            party_id,
            value_of_share_r % state.get("p", 0),
        )

    pom = multiply_bit_shares_by_powers_of_2(state.get("random_number_bit_shares", []))
    share_of_random_number = add_multiplied_shares(pom)

    state["random_number_share"] = share_of_random_number[1]

    return {
        "result": "Share of random number calculated successfully.",
    }


@app.post("/api/prepare-z-tables")
async def prepare_z_tables(
    values: PrepareZTablesData, current_user: dict = Depends(get_current_user)
):
    a_bin = binary(int(values.opened_a, 16))

    while len(a_bin) < values.l + values.k:
        a_bin.append(0)

    state["comparison_a_bits"] = a_bin

    state["z_table"] = [None for _ in range(values.l)]
    state["Z_table"] = [None for _ in range(values.l)]

    for i in range(values.l - 1, -1, -1):
        state["z_table"][i] = state.get("comparison_a_bits", [])[i]
        state["Z_table"][i] = state.get("comparison_a_bits", [])[i]

    return {
        "result": "Z tables prepared successfully.",
    }


@app.post("/api/calculate-additive-share-of-z-table/{index}")
async def calculate_additive_share_of_z_table_arguments(
    index: int, current_user: dict = Depends(get_current_user)
):
    first_share = state.get("comparison_a_bits", [])[index]
    second_share = state.get("random_number_bit_shares", [])[index][1]

    state["additive_share"] = (first_share + second_share) % state.get("p", 0)

    return {
        "result": f"Additive share of z table at index {index} calculated successfully."
    }


@app.post("/api/calculate-r-of-z-table/{index}")
async def calculate_r_of_z_table(
    index: int, current_user: dict = Depends(get_current_user)
):
    first_share = state.get("comparison_a_bits", [])[index]
    second_share = state.get("random_number_bit_shares", [])[index][1]

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

        await asyncio.gather(*tasks)

        return {
            "result": f"R for multipication of z table at index {index} calculated and shared"
        }


@app.post("/api/set-z-table-to-xor-share/{index}")
async def set_z_table_to_xor_share(
    index: int, current_user: dict = Depends(get_current_user)
):
    state["z_table"][index] = state["xor_share"]

    return {"result": f"z table at index {index} set to XOR share successfully."}


@app.post("/api/initialize-z-and-Z")
async def initialize_z_and_Z(
    values: InitializezAndZZData, current_user: dict = Depends(get_current_user)
):
    state["shares"]["z"] = state.get("z_table", [])[values.l - 1]
    state["shares"]["Z"] = state.get("Z_table", [])[values.l - 1]

    return {
        "result": "Shares z and Z initialized successfully.",
    }


@app.post("/api/prepare-for-next-romb/{index}")
async def prepare_for_next_romb(
    index: int, current_user: dict = Depends(get_current_user)
):
    state["shares"]["x"] = state.get("shares", {}).get("z", 0)
    state["shares"]["X"] = state.get("shares", {}).get("Z", 0)

    if index == 0:
        state["shares"]["y"] = 0
        state["shares"]["Y"] = 0
    else:
        state["shares"]["y"] = state.get("z_table", [])[index - 1]
        state["shares"]["Y"] = state.get("Z_table", [])[index - 1]

    return {
        "result": f"Prepared for next romb with index {index}. Shares x, X, y, Y set."
    }


@app.post(
    "/api/prepare-shares-for-res-xors/{comparison_a_bit_index}/{random_number_bit_share_index}"
)
async def prepare_shares_for_res_xors(
    comparison_a_bit_index: int,
    random_number_bit_share_index: int,
    current_user: dict = Depends(get_current_user),
):

    state["shares"]["a_l"] = state.get("comparison_a_bits", [])[comparison_a_bit_index]
    state["shares"]["r_l"] = state.get("random_number_bit_shares", [])[
        random_number_bit_share_index
    ][1]


app.include_router(auth.router)
app.include_router(initialization.router)
app.include_router(shares.router)
app.include_router(comparison.router)
app.include_router(redistribution.router)
app.include_router(multiplication.router)
app.include_router(xor.router)
app.include_router(reconstruction.router)
app.include_router(reset.router)
app.include_router(bidders.router)

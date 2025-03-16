import asyncio
from random import sample

from fastapi import FastAPI, HTTPException
from starlette.middleware.cors import CORSMiddleware

from api.config import STATUS, state
from api.parsers import (
    AComparisonData,
    CalculatedComparisonResultData,
    CalculateMultiplicativeShareData,
    InitialValues,
    RData,
    ShareData,
    SharedQData,
    SharedRData,
    XorData,
    ZComparisonData,
)
from api.utils import (
    Shamir,
    binary,
    binary_exponentiation,
    computate_coefficients,
    inverse_matrix_mod,
    multiply_matrix,
    reconstruct_secret,
    reset_state,
    send_get_request,
    send_post_request,
    validate_initialized,
    validate_initialized_array,
    validate_not_initialized,
)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

TEMPORARY_Z0 = 0
TEMPORARY_Z1 = 1


def get_temporary_zZ(index: int) -> int:
    """Safe accessor for temporary_zZ values"""
    if index not in [TEMPORARY_Z0, TEMPORARY_Z1]:
        raise ValueError("Invalid temporary_zZ index")
    return state["temporary_zZ"][index]


def set_temporary_zZ(index: int, value: int):
    """Safe mutator for temporary_zZ values"""
    if index not in [TEMPORARY_Z0, TEMPORARY_Z1]:
        raise ValueError("Invalid temporary_zZ index")
    state["temporary_zZ"][index] = value


def reset_temporary_zZ():
    """Reset temporary_zZ to initial state"""
    state["temporary_zZ"] = [0, 0]


@app.get("/api/status", status_code=200)
async def get_status():
    return {"status": state["status"].value}


@app.post("/api/initial-values", status_code=201)
async def set_initial_values(values: InitialValues):
    validate_not_initialized(
        ["t", "n", "id", "p", "shared_q", "shared_r", "parties", "client_shares"]
    )

    if values.t <= 0 or values.n <= 0 or 2 * values.t + 1 != values.n:
        raise HTTPException(status_code=400, detail="Invalid t or n values.")

    if int(values.p, 16) <= 0:
        raise HTTPException(status_code=400, detail="Prime number must be positive.")

    if len(values.parties) != values.n:
        raise HTTPException(
            status_code=400, detail="Number of parties does not match n."
        )

    state.update(
        {
            "t": values.t,
            "n": values.n,
            "id": values.id,
            "p": int(values.p, 16),
            "shared_q": [None] * values.n,
            "shared_r": [None] * values.n,
            "parties": values.parties,
            "client_shares": [],
            "status": STATUS.INITIALIZED,
        }
    )

    return {"result": "Initial values set"}


@app.get("/api/initial-values", status_code=200)
async def get_initial_values():
    if state["status"] == STATUS.NOT_INITIALIZED:
        raise HTTPException(status_code=400, detail="Server is not initialized.")

    validate_initialized(["t", "n", "p", "parties"])

    return {
        "t": state["t"],
        "n": state["n"],
        "p": hex(state["p"]),
        "parties": state["parties"],
    }


@app.post("/api/set-shares", status_code=201)
async def set_shares(values: ShareData):
    validate_initialized(["client_shares"])

    if (
        next((x for x, _ in state["client_shares"] if x == values.client_id), None)
        is not None
    ):
        raise HTTPException(
            status_code=400, detail="Shares already set for this client."
        )

    state["client_shares"].append((values.client_id, int(values.share)))

    return {"result": "Shares set"}


@app.post("/api/calculate-a-comparison", status_code=201)
async def calculate_a_comparison(values: AComparisonData):
    if len(state["client_shares"]) < 2:
        raise HTTPException(
            status_code=400, detail="At least two client shares must be configured."
        )

    if values.first_client_id == values.second_client_id:
        raise HTTPException(status_code=400, detail="Client IDs must be different.")

    first_client_share = next(
        (y for x, y in state["client_shares"] if x == values.first_client_id), None
    )
    second_client_share = next(
        (y for x, y in state["client_shares"] if x == values.second_client_id), None
    )

    if first_client_share is None or second_client_share is None:
        raise HTTPException(
            status_code=400, detail="Shares not set for one or both clients."
        )

    state["calculated_share"] = (
        pow(2, values.l + values.k + 2)
        + pow(2, values.l)
        + first_client_share
        - second_client_share
    )

    state["status"] = STATUS.SHARE_CALCULATED
    return {"result": "'A' for comparison calculated"}


@app.post("/api/calculate-z-comparison", status_code=201)
async def calculate_z(values: ZComparisonData):
    a_bin = binary(values.opened_a)

    while len(a_bin) < values.l + values.k + 2:
        a_bin.append(0)

    zZ = []

    for i in range(values.l):
        zZ.append([a_bin[i], a_bin[i]])

    zZ = list(reversed(zZ))
    zZ.append([0, 0])

    state["zZ"] = zZ
    reset_temporary_zZ()
    return {"result": "'Z' for comparison calculated"}


@app.post("/api/redistribute-q", status_code=201)
async def redistribute_q():
    if state["status"] != STATUS.INITIALIZED:
        raise HTTPException(
            status_code=400, detail="Server must be in initialized state."
        )

    validate_initialized(["t", "n", "p", "id", "parties", "shared_q"])

    q = Shamir(2 * state["t"], state["n"], 0, state["p"])

    tasks = []
    for i in range(state["n"]):
        if i == state["id"] - 1:
            state["shared_q"][i] = q[i][1]
            continue

        url = f"{state['parties'][i]}/api/receive-q-from-parties"
        json_data = {"party_id": state["id"], "shared_q": q[i][1]}
        tasks.append(send_post_request(url, json_data))

    await asyncio.gather(*tasks, return_exceptions=True)

    state["status"] = STATUS.Q_CALC_SHARED
    return {"result": "q calculated and shared"}


@app.post("/api/receive-q-from-parties", status_code=201)
async def set_received_q(values: SharedQData):
    validate_initialized(["shared_q"])

    if values.party_id > len(state["shared_q"]) or values.party_id < 1:
        raise HTTPException(status_code=400, detail="Invalid party id.")

    if state["shared_q"][values.party_id - 1] is not None:
        raise HTTPException(status_code=400, detail="q is already set from this party.")

    state["shared_q"][values.party_id - 1] = values.shared_q

    return {"result": "q received"}


@app.post("/api/redistribute-r", status_code=201)
async def redistribute_r(values: RData):
    # Validate server state
    if state["status"] != STATUS.Q_CALC_SHARED:
        raise HTTPException(
            status_code=400, detail="Server must be in q calculated and shared state."
        )

    # Validate required state variables
    validate_initialized(["client_shares", "n", "p", "t", "id", "shared_r", "parties"])
    validate_initialized_array(["shared_q"])

    # Extract multiplication factors based on the condition
    if not values.calculate_final_comparison_result:
        first_multiplication_factor = state["zZ"][
            values.zZ_first_multiplication_factor[0]
        ][values.zZ_first_multiplication_factor[1]]
        second_multiplication_factor = (
            state["temporary_zZ"][values.zZ_second_multiplication_factor[0]]
            if values.take_value_from_temporary_zZ
            else state["zZ"][values.zZ_second_multiplication_factor[0]][
                values.zZ_second_multiplication_factor[1]
            ]
        )

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
    if values.calculate_final_comparison_result:
        a_bin = binary(values.opened_a)

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
    tasks = []
    for i in range(state["n"]):
        if i == state["id"] - 1:
            state["shared_r"][i] = r[i]
            continue

        url = f"{state['parties'][i]}/api/receive-r-from-parties"
        json_data = {"party_id": state["id"], "shared_r": r[i]}
        tasks.append(send_post_request(url, json_data))

    await asyncio.gather(*tasks, return_exceptions=True)

    # Update state and return response
    state["status"] = STATUS.R_CALC_SHARED
    return {"result": "r calculated and shared"}


@app.post("/api/receive-r-from-parties", status_code=201)
async def set_received_r(values: SharedRData):
    validate_initialized(["shared_r"])

    if values.party_id > len(state["shared_r"]) or values.party_id < 1:
        raise HTTPException(status_code=400, detail="Invalid party id.")

    if state["shared_r"][values.party_id - 1] is not None:
        raise HTTPException(status_code=400, detail="r is already set from this party.")

    state["shared_r"][values.party_id - 1] = values.shared_r

    return {"result": "r received"}


@app.put("/api/calculate-multiplicative-share", status_code=201)
async def calculate_multiplicative_share(values: CalculateMultiplicativeShareData):
    if state["status"] != STATUS.R_CALC_SHARED:
        raise HTTPException(
            status_code=400, detail="Server must be in r calculated and shared state."
        )

    validate_initialized(["n", "p"])
    validate_initialized_array(["shared_r"])

    calculated_value = (
        sum([state["shared_r"][i] for i in range(state["n"])]) % state["p"]
    )

    if values.calculate_for_xor:
        state["xor_multiplication"] = calculated_value
    else:
        set_temporary_zZ(values.set_in_temporary_zZ_index, calculated_value)

    return {"result": "Multiplicative share calculated"}


@app.post("/api/xor", status_code=201)
async def addition(values: XorData):
    # Validate server state
    # if state["status"] != STATUS.INITIALIZED:
    #     raise HTTPException(
    #         status_code=400, detail="Server must be in initialized state."
    #     ) TODO

    # Extract the first multiplication factor
    first_multiplication_factor = state["zZ"][values.zZ_first_multiplication_factor[0]][
        values.zZ_first_multiplication_factor[1]
    ]

    # Extract the second multiplication factor based on the condition
    second_multiplication_factor = (
        get_temporary_zZ(values.zZ_second_multiplication_factor[0])
        if values.take_value_from_temporary_zZ
        else state["zZ"][values.zZ_second_multiplication_factor[0]][
            values.zZ_second_multiplication_factor[1]
        ]
    )

    # Calculate the result and update state
    result = (
        first_multiplication_factor
        + second_multiplication_factor
        - 2 * state["xor_multiplication"]
    )
    set_temporary_zZ(TEMPORARY_Z1, result)

    return {"result": "Additive share calculated"}


@app.post("/api/pop-zZ", status_code=201)
async def pop_zZ():
    state["zZ"][0] = [get_temporary_zZ(TEMPORARY_Z0), get_temporary_zZ(TEMPORARY_Z1)]
    state["zZ"].pop(1)
    reset_temporary_zZ()

    return {"result": "zZ popped"}


@app.post("/api/calculate-comparison-result", status_code=201)
async def calculate_comparison_result(values: CalculatedComparisonResultData):
    a_bin = binary(values.opened_a)

    while len(a_bin) < values.l + values.k + 2:
        a_bin.append(0)

    state["calculated_share"] = (
        a_bin[values.l] + state["zZ"][0][1] - 2 * state["xor_multiplication"]
    )

    state["status"] = STATUS.SHARE_CALCULATED


@app.get("/api/return-calculated-share", status_code=200)
async def get_calculated_share():
    validate_initialized(["calculated_share", "id"])

    return {"id": state["id"], "calculated_share": state["calculated_share"]}


@app.get("/api/reconstruct-secret", status_code=200)
async def return_secret():
    if state["status"] != STATUS.SHARE_CALCULATED:
        raise HTTPException(
            status_code=400,
            detail="Server must be in share calculated state.",
        )

    validate_initialized(["calculated_share", "parties", "id", "t", "p"])

    parties = [
        party for i, party in enumerate(state["parties"]) if i != state["id"] - 1
    ]
    selected_parties = sample(parties, state["t"] - 1)

    calculated_shares = []
    tasks = []
    for party in selected_parties:
        url = f"{party}/api/return-calculated-share"
        tasks.append(send_get_request(url))

    results = await asyncio.gather(*tasks, return_exceptions=True)

    for result in results:
        calculated_shares.append((result["id"], result["calculated_share"]))

    calculated_shares.append((state["id"], state["calculated_share"]))

    coefficients = computate_coefficients(calculated_shares, state["p"])

    secret = reconstruct_secret(calculated_shares, coefficients, state["p"])

    return {
        "secret": secret % state["p"]
    }  # TODO: Check if modulo p will not break the A comparison calculation


@app.post("/api/reset-calculation", status_code=201)
async def reset():
    if state["status"] == STATUS.NOT_INITIALIZED:
        raise HTTPException(status_code=400, detail="Server is not initialized.")

    validate_initialized(["n"])

    reset_state(["calculated_share", "xor_multiplication"])
    state["shared_q"] = [None] * state["n"]
    state["shared_r"] = [None] * state["n"]
    state["status"] = STATUS.INITIALIZED

    return {"result": "Reset calculation successful"}


@app.post("/api/reset-comparison", status_code=201)
async def reset():
    if state["status"] == STATUS.NOT_INITIALIZED:
        raise HTTPException(status_code=400, detail="Server is not initialized.")

    reset_state(
        ["calculated_share", "zZ"],
    )

    return {"result": "Reset comparison successful"}


@app.post("/api/factory-reset", status_code=201)
async def factory_reset():
    reset_state(
        [
            "t",
            "n",
            "id",
            "p",
            "parties",
            "shared_q",
            "shared_r",
            "client_shares",
            "calculated_share",
            "xor_multiplication",
        ]
    )

    state["status"] = STATUS.NOT_INITIALIZED

    return {"result": "Factory reset successful"}

import asyncio
from random import sample

from fastapi import FastAPI, HTTPException
from starlette.middleware.cors import CORSMiddleware

from api.config import STATUS, state
from api.parsers import (
    AComparisonData,
    AdditionData,
    InitialValues,
    RandomNumberBitSharesData,
    RData,
    ShareData,
    SharedQData,
    SharedRData,
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
            "random_number_bit_shares": [],
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


@app.post("/api/set-random-number-bit-shares", status_code=201)
async def set_random_number_bit_shares(values: RandomNumberBitSharesData):
    state["random_number_bit_shares"] = values.shares


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

    def multiply_bit_shares_by_powers_of_2(shares):
        multiplied_shares = []
        for i in range(len(shares)):
            multiplied_shares.append(2**i * shares[i])
        return multiplied_shares

    def add_multiplied_shares(multiplied_shares):
        share_r = multiplied_shares[0]
        for i in range(1, len(multiplied_shares)):
            share_r += multiplied_shares[i]
        return share_r

    pom = multiply_bit_shares_by_powers_of_2(state["random_number_bit_shares"])
    share_of_random_number = add_multiplied_shares(pom)

    state["random_number_share"] = share_of_random_number
    state["calculated_share"] = (
        pow(2, values.l + values.k + 2)
        - share_of_random_number
        + pow(2, values.l)
        + first_client_share
        - second_client_share
    )

    state["status"] = STATUS.SHARE_CALCULATED
    return {"result": "'A' for comparison calculated"}


@app.post("/api/calculate-z-comparison", status_code=201)
async def calculate_z(values: ZComparisonData):
    a_bin = binary(values.opened_a)
    r_prim_bin = binary(state["random_number_share"])

    while len(a_bin) < values.l + values.k + 2:
        a_bin.append(0)

    while len(r_prim_bin) < values.l + values.k + 2:
        r_prim_bin.append(0)

    zZ = []

    for i in range(values.l):
        zZ.append((a_bin[i] ^ r_prim_bin[i], a_bin[i]))

    zZ = list(reversed(zZ))
    zZ.append((0, 0))

    print("zZ: ", zZ)
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
    if state["status"] != STATUS.Q_CALC_SHARED:
        raise HTTPException(
            status_code=400, detail="Server must be in q calculated and shared state."
        )

    validate_initialized(["client_shares", "n", "p", "t", "id", "shared_r", "parties"])
    validate_initialized_array(["shared_q"])

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

    B = [list(range(1, state["n"] + 1)) for _ in range(state["n"])]

    for j in range(state["n"]):
        for k in range(state["n"]):
            B[j][k] = binary_exponentiation(B[j][k], j, state["p"])

    B_inv = inverse_matrix_mod(B, state["p"])

    P = [[0] * state["n"] for _ in range(state["n"])]

    for i in range(state["t"]):
        P[i][i] = 1

    A = multiply_matrix(multiply_matrix(B_inv, P, state["p"]), B, state["p"])

    multiplied_shares = (
        first_client_share * second_client_share + sum(state["shared_q"])
    ) % state["p"]

    r = [0] * state["n"]

    for i in range(state["n"]):
        r[i] = (multiplied_shares * A[state["id"] - 1][i]) % state["p"]

    tasks = []
    for i in range(state["n"]):
        if i == state["id"] - 1:
            state["shared_r"][i] = r[i]
            continue

        url = f"{state['parties'][i]}/api/receive-r-from-parties"
        json_data = {"party_id": state["id"], "shared_r": r[i]}
        tasks.append(send_post_request(url, json_data))

    await asyncio.gather(*tasks, return_exceptions=True)

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
async def calculate_multiplicative_share():
    if state["status"] != STATUS.R_CALC_SHARED:
        raise HTTPException(
            status_code=400, detail="Server must be in r calculated and shared state."
        )

    validate_not_initialized(["calculated_share"])
    validate_initialized(["n", "p"])
    validate_initialized_array(["shared_r"])

    state["calculated_share"] = (
        sum([state["shared_r"][i] for i in range(state["n"])]) % state["p"]
    )

    state["status"] = STATUS.SHARE_CALCULATED
    return {"result": "Multiplicative share calculated"}


@app.post("/api/addition", status_code=201)
async def addition(values: AdditionData):
    if state["status"] != STATUS.INITIALIZED:
        raise HTTPException(
            status_code=400, detail="Server must be in initialized state."
        )

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

    state["calculated_share"] = first_client_share + second_client_share

    state["status"] = STATUS.SHARE_CALCULATED
    return {"result": "Additive share calculated"}


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


@app.post("/api/reset", status_code=201)
async def reset():
    if state["status"] == STATUS.NOT_INITIALIZED:
        raise HTTPException(status_code=400, detail="Server is not initialized.")

    validate_initialized(["n"])

    reset_state(["calculated_share"])
    state["shared_q"] = [None] * state["n"]
    state["shared_r"] = [None] * state["n"]
    state["status"] = STATUS.INITIALIZED

    return {"result": "Reset successful"}


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
            "random_number_bit_shares",
            "random_number_share",
            "calculated_share",
        ]
    )

    state["status"] = STATUS.NOT_INITIALIZED

    return {"result": "Factory reset successful"}

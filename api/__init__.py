import asyncio
from random import sample

from fastapi import FastAPI, HTTPException
from starlette.middleware.cors import CORSMiddleware

from api.config import STATUS, state
from api.parsers import InitialValues, RData, ShareData, SharedRData
from api.utils import (
    binary_exponentiation,
    computate_coefficients,
    inverse_matrix_mod,
    is_initialized,
    is_not_initialized,
    multiply_matrix,
    reconstruct_secret,
    reset_state,
    send_get_request,
    send_post_request,
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
    is_not_initialized(["t", "n", "id", "p", "shared_r", "parties", "client_shares"])

    if len(values.parties) != values.n:
        raise HTTPException(
            status_code=400, detail="Number of parties does not match n."
        )

    state.update(
        {
            "t": values.t,
            "n": values.n,
            "id": values.id,
            "p": values.p,
            "shared_r": [None] * values.n,
            "parties": values.parties,
            "client_shares": [],
            "status": STATUS.INITIALIZED,
        }
    )

    return {"result": "Initial values set"}


@app.get("/api/initial-values", status_code=200)
async def get_initial_values():
    is_initialized(["t", "n", "id", "p", "shared_r", "parties"])

    return {
        "t": state["t"],
        "n": state["n"],
        "p": state["p"],
        "parties": state["parties"],
    }


@app.post("/api/set-shares", status_code=201)
async def set_shares(values: ShareData):
    state["client_shares"].append((values.client_id, values.share))

    return {"result": "Shares set"}


@app.post("/api/calculate-r", status_code=201)
async def calculate_r(values: RData):
    is_not_initialized(["r"])

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

    state["r"] = [0] * state["n"]

    multiplied_shares = (first_client_share * second_client_share) % state["p"]

    for i in range(state["n"]):
        state["r"][i] = (multiplied_shares * A[state["id"] - 1][i]) % state["p"]

    state["status"] = STATUS.R_SET
    return {"result": "r calculated"}


@app.post("/api/set-shared-r", status_code=201)
async def set_shared_r(values: SharedRData):
    if state["shared_r"][values.party_id - 1] is not None:
        raise HTTPException(status_code=400, detail="r is already shared.")

    state["shared_r"][values.party_id - 1] = values.shared_r

    return {"result": "r set"}


@app.put("/api/send-r-to-parties", status_code=201)
async def send_r_to_parties():
    tasks = []
    for i in range(state["n"]):
        if i == state["id"] - 1:
            state["shared_r"][i] = state["r"][i]
            continue

        url = f"{state['parties'][i]}/api/set-shared-r"
        json_data = {"party_id": state["id"], "shared_r": state["r"][i]}
        tasks.append(send_post_request(url, json_data))

    await asyncio.gather(*tasks)

    state["status"] = STATUS.R_SHARED
    return {"result": "r sent"}


@app.put("/api/calculate-multiplicative-share", status_code=201)
async def calculate_multiplicative_share():
    is_not_initialized(["multiplicative_share"])

    state["multiplicative_share"] = (
        sum([state["shared_r"][i] for i in range(state["n"])]) % state["p"]
    )

    state["status"] = STATUS.MULT_SHARE_CALCULATED
    return {"result": "Multiplicative share calculated"}


@app.get("/api/calculate-multiplicative-share", status_code=200)
async def get_multiplicative_share():
    is_initialized(["multiplicative_share"])

    return {"id": state["id"], "multiplicative_share": state["multiplicative_share"]}


@app.get("/api/reconstruct-secret", status_code=200)
async def return_secret():
    is_initialized(["multiplicative_share"])

    parties = [
        party for i, party in enumerate(state["parties"]) if i != state["id"] - 1
    ]
    selected_parties = sample(parties, state["t"] - 1)

    multiplicative_shares = []
    tasks = []
    for party in selected_parties:
        url = f"{party}/api/calculate-multiplicative-share"
        tasks.append(send_get_request(url))

    results = await asyncio.gather(*tasks, return_exceptions=True)

    for result in results:
        if isinstance(result, Exception):
            raise HTTPException(
                status_code=400,
                detail="Multiplicative share not calculated for one or more parties.",
            )
        multiplicative_shares.append((result["id"], result["multiplicative_share"]))

    multiplicative_shares.append((state["id"], state["multiplicative_share"]))

    coefficients = computate_coefficients(multiplicative_shares, state["p"])

    secret = reconstruct_secret(multiplicative_shares, coefficients, state["p"])

    return {"secret": secret % state["p"]}


@app.post("/api/reset", status_code=201)
async def reset():
    reset_state(["r", "multiplicative_share"])
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
            "shared_r",
            "r",
            "client_shares",
            "multiplicative_share",
        ]
    )

    state["status"] = STATUS.NOT_INITIALIZED

    return {"result": "Factory reset successful"}

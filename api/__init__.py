import asyncio
from random import sample

from fastapi import FastAPI, HTTPException
from starlette.middleware.cors import CORSMiddleware

from api.config import STATUS, state
from api.parsers import InitialValues, RData, ShareData, SharedQData, SharedRData
from api.utils import (
    Shamir,
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


@app.post("/api/redistribute-q", status_code=201)
async def redistribute_q():
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
    if state["shared_q"][values.party_id - 1] is not None:
        raise HTTPException(status_code=400, detail="q is already set from this party.")

    state["shared_q"][values.party_id - 1] = values.shared_q

    return {"result": "q received"}


@app.post("/api/redistribute-r", status_code=201)
async def redistribute_r(values: RData):
    for q in state["shared_q"]:
        if q is None:
            raise HTTPException(
                status_code=400, detail="q is not set for one or more parties."
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
    if state["shared_r"][values.party_id - 1] is not None:
        raise HTTPException(status_code=400, detail="r is already set from this party.")

    state["shared_r"][values.party_id - 1] = values.shared_r

    return {"result": "r received"}


@app.put("/api/calculate-multiplicative-share", status_code=201)
async def calculate_multiplicative_share():
    is_not_initialized(["multiplicative_share"])

    for r in state["shared_r"]:
        if r is None:
            raise HTTPException(
                status_code=400, detail="r is not set for one or more parties."
            )

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
        multiplicative_shares.append((result["id"], result["multiplicative_share"]))

    multiplicative_shares.append((state["id"], state["multiplicative_share"]))

    coefficients = computate_coefficients(multiplicative_shares, state["p"])

    secret = reconstruct_secret(multiplicative_shares, coefficients, state["p"])

    return {"secret": secret % state["p"]}


@app.post("/api/reset", status_code=201)
async def reset():
    reset_state(["multiplicative_share"])
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
            "shared_q" "shared_r",
            "client_shares",
            "multiplicative_share",
        ]
    )

    state["status"] = STATUS.NOT_INITIALIZED

    return {"result": "Factory reset successful"}

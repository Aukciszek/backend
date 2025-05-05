import asyncio
from datetime import datetime, timedelta, timezone
from random import sample

import jwt
from decouple import Csv
from decouple import config as dconfig
from fastapi import FastAPI, HTTPException, status
from passlib.context import CryptContext
from starlette.middleware.cors import CORSMiddleware
from supabase import create_client

from api.config import STATUS, state
from api.parsers import (
    AComparisonData,
    CalculatedComparisonResultData,
    CalculateMultiplicativeShareData,
    InitialValues,
    LoginData,
    RData,
    RegisterData,
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

SUPABASE_URL = dconfig("SUPABASE_URL", cast=str)
SUPABASE_KEY = dconfig("SUPABASE_KEY", cast=str)
SECRET_KEYS_JWT = dconfig("SECRET_KEYS_JWT", cast=Csv(str))
SERVERS = dconfig("SERVERS", cast=Csv(str))
ALGORITHM = dconfig("ALGORITHM", cast=str)
ACCESS_TOKEN_EXPIRE_MINUTES = dconfig("ACCESS_TOKEN_EXPIRE_MINUTES", cast=int)

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

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

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

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


@app.get(
    "/api/status",
    status_code=status.HTTP_200_OK,
    tags=["Status"],
    summary="Get the current server status",
    response_description="Returns the current status of the server.",
    responses={
        200: {
            "description": "Server is operational.",
            "content": {"application/json": {"example": {"status": "NOT_INITIALIZED"}}},
        }
    },
)
async def get_status():
    """
    Returns the current status of the server.
    """
    return {"status": state["status"].value}


@app.post(
    "/api/initial-values",
    status_code=status.HTTP_200_OK,
    tags=["Initialization"],
    summary="Set initial values for the MPC protocol",
    response_description="Initial values have been successfully set.",
    responses={
        200: {
            "description": "Initial values set successfully.",
            "content": {
                "application/json": {"example": {"result": "Initial values set"}}
            },
        },
        400: {
            "description": "Invalid input values.",
            "content": {
                "application/json": {"example": {"detail": "Invalid t or n values."}}
            },
        },
    },
)
async def set_initial_values(values: InitialValues):
    """
    Sets the initial values required for the MPC protocol.

    Request Body:
    - `t`: The threshold value.
    - `n`: The total number of parties.
    - `id`: The ID of this party.
    - `p`: The prime number.
    - `parties`: List of URLs of all parties.

    """
    validate_not_initialized(
        ["t", "n", "id", "p", "shared_q", "shared_r", "parties", "client_shares"]
    )

    if values.t <= 0 or values.n <= 0 or 2 * values.t + 1 != values.n:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid t or n values."
        )

    if int(values.p, 16) <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Prime number must be positive.",
        )

    if len(values.parties) != values.n:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Number of parties does not match n.",
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


@app.get(
    "/api/initial-values",
    status_code=status.HTTP_200_OK,
    tags=["Initialization"],
    summary="Get the currently set initial values",
    response_description="Returns the currently set initial values.",
    responses={
        200: {
            "description": "Successfully retrieved initial values.",
            "content": {
                "application/json": {
                    "example": {
                        "t": 1,
                        "n": 3,
                        "p": "0xfffffffffffffffffffffffffffffffeffffffffffffffff",
                        "parties": [
                            "http://localhost:5001",
                            "http://localhost:5002",
                            "http://localhost:5003",
                        ],
                    }
                }
            },
        },
        400: {
            "description": "Server is not initialized.",
            "content": {
                "application/json": {
                    "example": {"detail": "Server is not initialized."}
                }
            },
        },
    },
)
async def get_initial_values():
    """
    Returns the currently set initial values.
    """
    if state["status"] == STATUS.NOT_INITIALIZED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Server is not initialized."
        )

    validate_initialized(["t", "n", "p", "parties"])

    return {
        "t": state["t"],
        "n": state["n"],
        "p": hex(state["p"]),
        "parties": state["parties"],
    }


@app.post(
    "/api/set-shares",
    status_code=status.HTTP_201_CREATED,
    tags=["Shares"],
    summary="Set a client's share",
    response_description="Client's share has been successfully set.",
    responses={
        201: {
            "description": "Shares set successfully.",
            "content": {"application/json": {"example": {"result": "Shares set"}}},
        },
        400: {
            "description": "Shares already set for this client.",
            "content": {
                "application/json": {
                    "example": {"detail": "Shares already set for this client."}
                }
            },
        },
    },
)
async def set_shares(values: ShareData):
    """
    Sets a client's share.

    Request Body:
    - `client_id`: The ID of the client.
    - `share`: The share value.
    """
    validate_initialized(["client_shares"])

    if (
        next((x for x, _ in state["client_shares"] if x == values.client_id), None)
        is not None
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Shares already set for this client.",
        )

    state["client_shares"].append((values.client_id, int(values.share, 16)))

    return {"result": "Shares set"}


@app.post(
    "/api/calculate-a-comparison",
    status_code=status.HTTP_201_CREATED,
    tags=["Comparison"],
    summary="Calculate 'A' for comparison",
    response_description="'A' for comparison has been calculated.",
    responses={
        201: {
            "description": "'A' for comparison calculated.",
            "content": {
                "application/json": {
                    "example": {"result": "'A' for comparison calculated"}
                }
            },
        },
        400: {
            "description": "Invalid input or not enough shares.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "At least two client shares must be configured."
                    }
                }
            },
        },
    },
)
async def calculate_a_comparison(values: AComparisonData):
    """
    Calculates the 'A' value required for the comparison protocol.

    Request Body:
    - `first_client_id`: The ID of the first client.
    - `second_client_id`: The ID of the second client.
    """
    if len(state["client_shares"]) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least two client shares must be configured.",
        )

    if values.first_client_id == values.second_client_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Client IDs must be different.",
        )

    first_client_share = next(
        (y for x, y in state["client_shares"] if x == values.first_client_id), None
    )
    second_client_share = next(
        (y for x, y in state["client_shares"] if x == values.second_client_id), None
    )

    if first_client_share is None or second_client_share is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Shares not set for one or both clients.",
        )

    state["calculated_share"] = (
        # pow(2, values.l + values.k + 2)
        # + pow(2, values.l)
        first_client_share
        - second_client_share
    )

    state["status"] = STATUS.SHARE_CALCULATED
    return {"result": "'A' for comparison calculated"}


@app.post(
    "/api/calculate-z-comparison",
    status_code=status.HTTP_201_CREATED,
    tags=["Comparison"],
    summary="Calculate 'Z' for comparison",
    response_description="'Z' for comparison has been calculated.",
    responses={
        201: {
            "description": "'Z' for comparison calculated.",
            "content": {
                "application/json": {
                    "example": {"result": "'Z' for comparison calculated"}
                }
            },
        }
    },
)
async def calculate_z(values: ZComparisonData):
    """
    Calculates the 'Z' value required for the comparison protocol.

    Request Body:
    - `opened_a`: Opened value of a
    - `l`: length
    - `k`: kappa
    """
    a_bin = binary(int(values.opened_a, 16))

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


@app.post(
    "/api/redistribute-q",
    status_code=status.HTTP_201_CREATED,
    tags=["Redistribution"],
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

    tasks = []
    for i in range(state["n"]):
        if i == state["id"] - 1:
            state["shared_q"][i] = q[i][1]
            continue

        url = f"{state['parties'][i]}/api/receive-q-from-parties"
        json_data = {"party_id": state["id"], "shared_q": hex(q[i][1])}
        tasks.append(send_post_request(url, json_data))

    await asyncio.gather(*tasks, return_exceptions=True)

    state["status"] = STATUS.Q_CALC_SHARED
    return {"result": "q calculated and shared"}


@app.post(
    "/api/receive-q-from-parties",
    status_code=status.HTTP_201_CREATED,
    tags=["Redistribution"],
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
     - `shared_q`: the q share
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


@app.post(
    "/api/redistribute-r",
    status_code=status.HTTP_201_CREATED,
    tags=["Redistribution"],
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
    - `take_value_from_temporary_zZ`: Flag indicating whether to take the second value from temporary_zZ.
    - `zZ_first_multiplication_factor`: The first multiplication factor from zZ.
    - `zZ_second_multiplication_factor`: The second multiplication factor from zZ.
    - `calculate_final_comparison_result`: Flag indicating whether to calculate the final comparison result.
    - `opened_a`: Opened value of a
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
    tasks = []
    for i in range(state["n"]):
        if i == state["id"] - 1:
            state["shared_r"][i] = r[i]
            continue

        url = f"{state['parties'][i]}/api/receive-r-from-parties"
        json_data = {"party_id": state["id"], "shared_r": hex(r[i])}
        tasks.append(send_post_request(url, json_data))

    await asyncio.gather(*tasks, return_exceptions=True)

    # Update state and return response
    state["status"] = STATUS.R_CALC_SHARED
    return {"result": "r calculated and shared"}


@app.post(
    "/api/receive-r-from-parties",
    status_code=status.HTTP_201_CREATED,
    tags=["Redistribution"],
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
    - `shared_r`: the r share
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


@app.put(
    "/api/calculate-multiplicative-share",
    status_code=status.HTTP_201_CREATED,
    tags=["Multiplication"],
    summary="Calculate multiplicative share",
    response_description="Multiplicative share has been calculated.",
    responses={
        201: {
            "description": "Multiplicative share calculated.",
            "content": {
                "application/json": {
                    "example": {"result": "Multiplicative share calculated"}
                }
            },
        },
        400: {
            "description": "Server must be in 'r' calculated and shared state.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Server must be in r calculated and shared state."
                    }
                }
            },
        },
    },
)
async def calculate_multiplicative_share(values: CalculateMultiplicativeShareData):
    """
    Calculates a multiplicative share used in secure multiplication protocols.

    Request Body:
    - `set_in_temporary_zZ_index`: Index to set the calculated value in temporary_zZ.
    - `calculate_for_xor`: Flag indicating whether to calculate for XOR.
    """
    if state["status"] != STATUS.R_CALC_SHARED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Server must be in r calculated and shared state.",
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


@app.post(
    "/api/xor",
    status_code=status.HTTP_201_CREATED,
    tags=["XOR"],
    summary="Perform secure XOR operation",
    response_description="Additive share resulting from XOR operation has been calculated.",
    responses={
        201: {
            "description": "Additive share calculated.",
            "content": {
                "application/json": {"example": {"result": "Additive share calculated"}}
            },
        },
        # 400: {"description": "Server must be in initialized state.", "content": {"application/json": {"example": {"detail": "Server must be in initialized state."}}}}, #TODO
    },
)
async def addition(values: XorData):
    """
    Performs a secure XOR operation on shared values.

    Request Body:
    - `take_value_from_temporary_zZ`: Flag indicating whether to take the second value from temporary_zZ.
    - `zZ_first_multiplication_factor`: The first multiplication factor from zZ.
    - `zZ_second_multiplication_factor`: The second multiplication factor from zZ.
    """
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


@app.post(
    "/api/pop-zZ",
    status_code=status.HTTP_201_CREATED,
    tags=["Multiplication"],
    summary="Pop a value from zZ",
    response_description="Value has been popped from zZ.",
    responses={
        201: {
            "description": "zZ popped.",
            "content": {"application/json": {"example": {"result": "zZ popped"}}},
        }
    },
)
async def pop_zZ():
    """
    Pops a value from the zZ.
    """
    state["zZ"][0] = [get_temporary_zZ(TEMPORARY_Z0), get_temporary_zZ(TEMPORARY_Z1)]
    state["zZ"].pop(1)
    reset_temporary_zZ()

    return {"result": "zZ popped"}


@app.post(
    "/api/calculate-comparison-result",
    status_code=status.HTTP_201_CREATED,
    tags=["Comparison"],
    summary="Calculate the final comparison result",
    response_description="Final comparison result has been calculated.",
    responses={
        201: {
            "description": "Comparison result calculated.",
            "content": {
                "application/json": {
                    "example": {"result": "Comparison result calculated"}
                }
            },
        },
    },
)
async def calculate_comparison_result(values: CalculatedComparisonResultData):
    """
    Calculates the final result of the comparison.

    Request Body:
    - `opened_a`: Opened value of a
    - `l`: length
    - `k`: kappa
    """
    a_bin = binary(int(values.opened_a, 16))

    while len(a_bin) < values.l + values.k + 2:
        a_bin.append(0)

    state["calculated_share"] = (
        a_bin[values.l] + state["zZ"][0][1] - 2 * state["xor_multiplication"]
    )

    state["status"] = STATUS.SHARE_CALCULATED


@app.get(
    "/api/return-calculated-share",
    status_code=status.HTTP_200_OK,
    tags=["Reconstruction"],
    summary="Return the calculated share",
    response_description="Returns the calculated share.",
    responses={
        200: {
            "description": "Calculated share returned.",
            "content": {
                "application/json": {"example": {"id": 1, "calculated_share": 12345}}
            },
        }
    },
)
async def get_calculated_share():
    """
    Returns the calculated share.
    """
    validate_initialized(["calculated_share", "id"])

    return {"id": state["id"], "calculated_share": state["calculated_share"]}


@app.get(
    "/api/reconstruct-secret",
    status_code=status.HTTP_200_OK,
    tags=["Reconstruction"],
    summary="Reconstruct the secret",
    response_description="Returns the reconstructed secret.",
    responses={
        200: {
            "description": "Secret reconstructed.",
            "content": {"application/json": {"example": {"secret": 654321}}},
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


@app.post(
    "/api/reset-calculation",
    status_code=status.HTTP_201_CREATED,
    tags=["Reset"],
    summary="Reset the calculation",
    response_description="Calculation has been reset.",
    responses={
        201: {
            "description": "Calculation reset successful.",
            "content": {
                "application/json": {
                    "example": {"result": "Reset calculation successful"}
                }
            },
        }
    },
)
async def reset_calculation():
    """
    Resets the calculation, clearing intermediate values.
    """
    if state["status"] == STATUS.NOT_INITIALIZED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Server is not initialized."
        )

    validate_initialized(["n"])

    reset_state(["calculated_share", "xor_multiplication"])
    state["shared_q"] = [None] * state["n"]
    state["shared_r"] = [None] * state["n"]
    state["status"] = STATUS.INITIALIZED

    return {"result": "Reset calculation successful"}


@app.post(
    "/api/reset-comparison",
    status_code=status.HTTP_201_CREATED,
    tags=["Reset"],
    summary="Reset the comparison",
    response_description="Comparison has been reset.",
    responses={
        201: {
            "description": "Comparison reset successful.",
            "content": {
                "application/json": {
                    "example": {"result": "Reset comparison successful"}
                }
            },
        }
    },
)
async def reset_comparison():
    """
    Resets the comparison, clearing comparison-specific values.
    """
    if state["status"] == STATUS.NOT_INITIALIZED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Server is not initialized."
        )

    validate_initialized(["n"])

    reset_state(["calculated_share", "zZ", "xor_multiplication", "temporary-zZ"])

    state["shared_q"] = [None] * state["n"]
    state["shared_r"] = [None] * state["n"]

    state["status"] = STATUS.INITIALIZED

    return {"result": "Reset comparison successful"}


@app.post(
    "/api/factory-reset",
    status_code=status.HTTP_201_CREATED,
    tags=["Reset"],
    summary="Perform a factory reset",
    response_description="Server has been factory reset.",
    responses={
        201: {
            "description": "Factory reset successful.",
            "content": {
                "application/json": {"example": {"result": "Factory reset successful"}}
            },
        }
    },
)
async def factory_reset():
    """
    Resets the server to its initial, uninitialized state.
    """
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
            "temporary-zZ",
            "zZ",
        ]
    )

    state["status"] = STATUS.NOT_INITIALIZED

    return {"result": "Factory reset successful"}


@app.get(
    "/api/get-bidders",
    status_code=status.HTTP_200_OK,
    tags=["Bidders"],
    summary="Get the list of bidders",
    response_description="Returns a list of bidder IDs.",
    responses={
        200: {
            "description": "List of bidders retrieved.",
            "content": {"application/json": {"example": {"bidders": [1, 2, 3]}}},
        }
    },
)
async def get_bidders():
    """
    Retrieves the list of bidders (client IDs) who have submitted shares.
    """
    if state["status"] == STATUS.NOT_INITIALIZED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Server is not initialized."
        )

    validate_initialized(["n"])

    bidders = [item[0] for item in state["client_shares"]]

    return {"bidders": bidders}


def create_access_token(data: dict, expires_delta: timedelta | None = None):
    """
    Generates a JWT access token.
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})

    encoded_jwt = []
    for i, secret_key_jwt in enumerate(SECRET_KEYS_JWT):
        encoded_jwt.append(
            {
                "access_token": jwt.encode(
                    to_encode, secret_key_jwt, algorithm=ALGORITHM
                ),
                "server": SERVERS[i],
            }
        )

    return encoded_jwt


@app.post(
    "/api/auth/register",
    status_code=status.HTTP_201_CREATED,
    tags=["Authentication"],
    summary="Register a new user",
    response_description="User registered successfully.",
    responses={
        201: {
            "description": "User registered.",
            "content": {
                "application/json": {
                    "example": {
                        "access_tokens": [
                            {"access_token": "token1", "server": "server1"},
                            {"access_token": "token2", "server": "server2"},
                        ],
                        "token_type": "bearer",
                    }
                }
            },
        },
        409: {
            "description": "Email already registered.",
            "content": {
                "application/json": {"example": {"detail": "Email already registered."}}
            },
        },
    },
)
async def register(user_req_data: RegisterData):
    """
    Registers a new user in the system and returns access tokens.

    Request Body:
    - `email`: The email address of the user.
    - `password`: The password of the user.
    - `admin`: Boolean indicating if the user is an administrator.
    """
    user = (
        supabase.table("users").select("*").eq("email", user_req_data.email).execute()
    )

    if user.data == []:
        supabase.table("users").insert(
            {
                "email": user_req_data.email,
                "password": pwd_context.hash(user_req_data.password),
                "admin": user_req_data.admin,
            }
        ).execute()
    else:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Email already registered."
        )

    user = (
        supabase.table("users").select("*").eq("email", user_req_data.email).execute()
    )

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_tokens = create_access_token(
        data={"uid": user.data[0]["uid"], "admin": user.data[0]["admin"]},
        expires_delta=access_token_expires,
    )

    return {"access_tokens": access_tokens, "token_type": "bearer"}


@app.post(
    "/api/auth/login",
    status_code=status.HTTP_200_OK,
    tags=["Authentication"],
    summary="Login a user",
    response_description="User logged in successfully.",
    responses={
        200: {
            "description": "User logged in.",
            "content": {
                "application/json": {
                    "example": {
                        "access_tokens": [
                            {"access_token": "token1", "server": "server1"},
                            {"access_token": "token2", "server": "server2"},
                        ],
                        "token_type": "bearer",
                    }
                }
            },
        },
        404: {
            "description": "Incorrect email or password.",
            "content": {
                "application/json": {
                    "example": {"detail": "Incorrect email or password."}
                }
            },
        },
        401: {
            "description": "Incorrect email or password.",
            "content": {
                "application/json": {
                    "example": {"detail": "Incorrect email or password."}
                }
            },
        },
    },
)
async def login(user_req_data: LoginData):
    """
    Logs in a user and returns an access tokens.

    Request Body:
    - `email`: The email address of the user.
    - `password`: The password of the user.
    """
    user = (
        supabase.table("users").select("*").eq("email", user_req_data.email).execute()
    )

    if user.data == []:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Incorrect email or password."
        )
    elif not pwd_context.verify(user_req_data.password, user.data[0]["password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
        )

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    access_tokens = create_access_token(
        data={"uid": user.data[0]["uid"], "admin": user.data[0]["admin"]},
        expires_delta=access_token_expires,
    )

    return {"access_tokens": access_tokens, "token_type": "bearer"}

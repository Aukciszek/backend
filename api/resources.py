import asyncio
from random import sample

import aiohttp
from config import STATUS, state
from flask import abort
from flask_restful import Resource
from parsers import (
    calculate_r_args,
    set_initial_values_args,
    set_r_args,
    set_shares_args,
)
from utils import (
    binary_exponentiation,
    computate_coefficients,
    inverse_matrix_mod,
    multiply_matrix,
    reconstruct_secret,
)


class Status(Resource):
    def get(self):
        return {"status": state["status"].value}, 200


class SetInitialValues(Resource):
    def post(self):
        if (
            state["t"] is not None
            or state["n"] is not None
            or state["id"] is not None
            or state["p"] is not None
            or state["shared_r"] is not None
            or state["parties"] is not None
        ):
            abort(400, "Initial values already set.")

        args = set_initial_values_args.parse_args()
        state["t"] = args["t"]
        state["n"] = args["n"]
        state["id"] = args["id"]
        state["p"] = args["p"]
        state["shared_r"] = [None] * state["n"]
        parties = args["parties"]

        if len(parties) != state["n"]:
            abort(400, "Number of parties does not match n.")

        state["parties"] = parties

        state["status"] = STATUS.INITIALIZED
        return {"result": "Initial values set"}, 201

    def get(self):
        if (
            state["t"] is None
            or state["n"] is None
            or state["id"] is None
            or state["p"] is None
            or state["shared_r"] is None
            or state["parties"] is None
        ):
            abort(400, "Initial values not set.")

        return {
            "t": state["t"],
            "n": state["n"],
            "id": state["id"],
            "p": state["p"],
            "parties": state["parties"],
        }, 200


class SetShares(Resource):
    def post(self):
        state["client_shares"].append(
            (
                set_shares_args.parse_args()["client_id"],
                set_shares_args.parse_args()["share"],
            )
        )

        return {"result": "Shares set"}, 201


class CalculateR(Resource):
    def post(self):
        if state["r"] is not None:
            abort(400, "r already calculated.")

        args = calculate_r_args.parse_args()
        first_client_id = args["first_client_id"]
        second_client_id = args["second_client_id"]
        first_client_share = next(
            (y for x, y in state["client_shares"] if x == first_client_id), None
        )
        second_client_share = next(
            (y for x, y in state["client_shares"] if x == second_client_id), None
        )

        if first_client_share is None or second_client_share is None:
            abort(400, "Shares not set for one or both clients.")

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
        return {"result": "r calculated"}, 201


class SetSharedRFromParty(Resource):
    def post(self):
        args = set_r_args.parse_args()
        party_id = args["party_id"]
        shared_r = args["shared_r"]

        if state["shared_r"][party_id - 1] is not None:
            abort(400, "r already set for this party.")

        state["shared_r"][party_id - 1] = shared_r

        return {"result": "r set"}, 201


class SendRToParties(Resource):
    async def send_post_request(self, url, json_data):
        """Send a POST request asynchronously using aiohttp."""
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(url, json=json_data) as response:
                    if response.status != 201:
                        raise ValueError(
                            f"Error: Received status code {response.status} for URL {url}"
                        )
            except aiohttp.ClientError as e:
                raise ValueError(f"HTTP error occurred for {url}: {e}")
            except Exception as e:
                raise ValueError(f"Unexpected error occurred for {url}: {e}")

    async def send_all_requests(self):
        """Send requests to all parties asynchronously."""
        tasks = []
        for i in range(state["n"]):
            if i == state["id"] - 1:
                state["shared_r"][i] = state["r"][i]
                continue

            url = f"{state['parties'][i]}/api/set-shared-r/"
            json_data = {"party_id": state["id"], "shared_r": state["r"][i]}
            tasks.append(self.send_post_request(url, json_data))

        await asyncio.gather(*tasks)

    def get(self):
        """Handle the GET request."""
        asyncio.run(self.send_all_requests())
        state["status"] = STATUS.R_SHARED
        return {"result": "r sent"}, 200


class CalculateMultiplicativeShare(Resource):
    def put(self):
        if state["multiplicative_share"] is not None:
            abort(400, "Multiplicative share already calculated.")

        state["multiplicative_share"] = (
            sum([state["shared_r"][i] for i in range(state["n"])]) % state["p"]
        )

        state["status"] = STATUS.MULT_SHARE_CALCULATED
        return {"result": "Multiplicative share calculated"}, 201

    def get(self):
        if state["multiplicative_share"] is None:
            abort(400, "Multiplicative share not calculated.")

        return {
            "id": state["id"],
            "multiplicative_share": state["multiplicative_share"],
        }, 200


class ResonstructSecret(Resource):
    async def fetch_multiplicative_share(self, url):
        """Fetch multiplicative share asynchronously using aiohttp."""
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url) as response:
                    if response.status == 400:
                        raise ValueError("Multiplicative share not calculated.")
                    elif response.status != 200:
                        raise ValueError(
                            f"Error: Received status code {response.status} for URL {url}"
                        )
                    return await response.json()
            except aiohttp.ClientError as e:
                raise ValueError(f"HTTP error occurred for {url}: {e}")
            except Exception as e:
                raise ValueError(f"Unexpected error occurred for {url}: {e}")

    async def gather_multiplicative_shares(self, selected_parties):
        """Gather multiplicative shares asynchronously from selected parties."""
        tasks = []
        for party in selected_parties:
            url = f"{party}/api/calculate-multiplicative-share/"
            tasks.append(self.fetch_multiplicative_share(url))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        multiplicative_shares = []
        for result in results:
            if isinstance(result, Exception):
                abort(
                    400, "Multiplicative share not calculated for one or more parties."
                )
            multiplicative_shares.append((result["id"], result["multiplicative_share"]))

        return multiplicative_shares

    def get(self):
        """Handle the GET request."""
        if state["multiplicative_share"] is None:
            abort(400, "Multiplicative share not calculated.")

        parties = [
            party for i, party in enumerate(state["parties"]) if i != state["id"] - 1
        ]
        selected_parties = sample(parties, state["t"] - 1)

        multiplicative_shares = asyncio.run(
            self.gather_multiplicative_shares(selected_parties)
        )

        multiplicative_shares.append((state["id"], state["multiplicative_share"]))

        coefficients = computate_coefficients(multiplicative_shares, state["p"])

        secret = reconstruct_secret(multiplicative_shares, coefficients, state["p"])

        return {"secret": secret % state["p"]}, 200


class Reset(Resource):
    def post(self):
        state["r"] = None
        state["shared_r"] = [None] * state["n"]
        state["multiplicative_share"] = None
        state["status"] = STATUS.INITIALIZED

        return {"result": "Reset successful"}, 201


class FactoryReset(Resource):
    def post(self):
        state["t"] = None
        state["n"] = None
        state["id"] = None
        state["p"] = None
        state["parties"] = None
        state["client_shares"] = []
        state["shared_r"] = None
        state["r"] = None
        state["multiplicative_share"] = None
        state["status"] = STATUS.NOT_INITIALIZED

        return {"result": "Factory reset successful"}, 201

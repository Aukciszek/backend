import requests
from config import state
from flask import abort
from flask_restful import Resource
from parsers import (
    calculate_r_args,
    set_initial_values_args,
    set_r_args,
    set_shares_args,
)
from shamir_functions import binary_exponentiation, inverse_matrix_mod, multiply_matrix


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

        return {"result": "Initial values set"}, 201


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

        first_client_share = next(
            (y for x, y in state["client_shares"] if x == first_client_id), None
        )
        second_client_share = next(
            (y for x, y in state["client_shares"] if x == second_client_id), None
        )
        multiplied_shares = (first_client_share * second_client_share) % state["p"]

        for i in range(state["n"]):
            state["r"][i] = (multiplied_shares * A[state["id"] - 1][i]) % state["p"]

        return {"result": "r calculated"}, 201


class SetR(Resource):
    def post(self):
        args = set_r_args.parse_args()
        party_id = args["party_id"]
        local_shared_r = args["shared_r"]

        if state["shared_r"][party_id - 1] is not None:
            abort(400, "r already set for this party.")

        state["shared_r"][party_id - 1] = local_shared_r

        return {"result": "r set"}, 201


class SendR(Resource):
    def get(self):
        for i in range(state["n"]):
            if i == state["id"] - 1:
                state["shared_r"][i] = state["r"][i]
                continue

            requests.post(
                f"{state["parties"][i]}/api/set-r/",
                json={"party_id": state["id"], "shared_r": state["r"][i]},
            )

        return {"result": "r sent"}, 200


class CalculateMultiplicativeShare(Resource):
    def put(self):
        if state["multiplicative_share"] is not None:
            abort(400, "Multiplicative share already calculated.")

        state["multiplicative_share"] = (
            sum([state["shared_r"][i] for i in range(state["n"])]) % state["p"]
        )

        return {"result": "Multiplicative share calculated"}, 201

    def get(self):
        return {
            "id": state["id"],
            "multiplicative_share": state["multiplicative_share"],
        }, 200


class Reset(Resource):
    def post(self):
        state["r"] = None
        state["shared_r"] = [None] * state["n"]
        state["multiplicative_share"] = None

        return {"result": "Reset successful"}, 200

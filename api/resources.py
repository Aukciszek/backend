import requests
from flask_restful import Resource

from config import state
from parsers import (
    calculate_r_args,
    set_initial_values_args,
    set_parties_args,
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
        ):
            return {"result": "Initial values already set"}, 400

        args = set_initial_values_args.parse_args()
        state["t"] = args["t"]
        state["n"] = args["n"]
        state["id"] = args["id"]
        state["p"] = args["p"]
        state["shared_r"] = [None] * state["n"]

        return {"result": "Initial values set"}, 201


class SetParties(Resource):
    def post(self):

        if state["parties"] is not None:
            return {"result": "Parties already set"}, 400

        args = set_parties_args.parse_args()
        local_parties = args["parties"]

        if len(local_parties) != state["n"]:
            return {"result": "Invalid number of parties"}, 400

        state["parties"] = local_parties

        return {"result": "Parties set"}, 201


class SetShares(Resource):
    def post(self):
        state["client_shares"].append(
            (
                set_shares_args.parse_args()["client_id"],
                set_shares_args.parse_args()["share"],
            )
        )

        return {"result": "Shares set"}, 201


class CalculateA(Resource):
    def post(self):
        if state["A"] is not None:
            return {"result": "A already calculated"}, 400

        B = [list(range(1, state["n"] + 1)) for _ in range(state["n"])]

        for j in range(state["n"]):
            for k in range(state["n"]):
                B[j][k] = binary_exponentiation(B[j][k], j, state["p"])

        B_inv = inverse_matrix_mod(B, state["p"])

        P = [[0] * state["n"] for _ in range(state["n"])]

        for i in range(state["t"]):
            P[i][i] = 1

        state["A"] = multiply_matrix(
            multiply_matrix(B_inv, P, state["p"]), B, state["p"]
        )

        return {"result": "A calculated"}, 201


class CalculateR(Resource):
    def post(self):
        if state["r"] is not None:
            return {"result": "r already calculated"}, 400

        args = calculate_r_args.parse_args()
        first_client_id = args["first_client_id"]
        second_client_id = args["second_client_id"]

        state["r"] = [0] * state["n"]

        first_client_share = next(
            (y for x, y in state["client_shares"] if x == first_client_id), None
        )
        second_client_share = next(
            (y for x, y in state["client_shares"] if x == second_client_id), None
        )
        multiplied_shares = (first_client_share * second_client_share) % state["p"]

        for i in range(state["n"]):
            state["r"][i] = (
                multiplied_shares * state["A"][state["id"] - 1][i]
            ) % state["p"]

        return {"result": "r calculated"}, 201


class SetR(Resource):
    def post(self):
        args = set_r_args.parse_args()
        party_id = args["party_id"]
        local_shared_r = args["shared_r"]

        if state["shared_r"][party_id - 1] is not None:
            return {"result": "r already set."}, 400

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
            raise ValueError("Coefficient already calculated.")

        state["multiplicative_share"] = (
            sum([state["shared_r"][i] for i in range(state["n"])]) % state["p"]
        )

        return {"result": "Multiplicative share calculated"}, 201

    def get(self):
        return {"multiplicative_share": state["multiplicative_share"]}, 200


class Reset(Resource):
    def post(self):
        state["r"] = None
        state["shared_r"] = [None] * state["n"]
        state["multiplicative_share"] = None

        return {"result": "Reset successful"}, 200

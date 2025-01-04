from flask_restful import reqparse

set_initial_values_args = reqparse.RequestParser()
set_initial_values_args.add_argument("t", type=int, help="t", required=True)
set_initial_values_args.add_argument("n", type=int, help="n", required=True)
set_initial_values_args.add_argument("id", type=int, help="ID", required=True)
set_initial_values_args.add_argument("p", type=int, help="p", required=True)
set_initial_values_args.add_argument(
    "parties", type=list, help="List of parties", required=True, location="json"
)

set_shares_args = reqparse.RequestParser()
set_shares_args.add_argument("client_id", type=int, help="Client ID", required=True)
set_shares_args.add_argument("share", type=int, help="Client share", required=True)

calculate_r_args = reqparse.RequestParser()
calculate_r_args.add_argument(
    "first_client_id", type=int, help="First client ID", required=True
)
calculate_r_args.add_argument(
    "second_client_id",
    type=int,
    help="Second client ID",
    required=True,
)

set_r_args = reqparse.RequestParser()
set_r_args.add_argument("party_id", type=int, help="Party ID", required=True)
set_r_args.add_argument("shared_r", type=int, help="Shared r", required=True)

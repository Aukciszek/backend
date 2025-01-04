import argparse

parser = argparse.ArgumentParser(description="Aukciszek API")
parser.add_argument("--port", type=int, required=True, help="Port number")
args = parser.parse_args()

state = {
    "t": None,
    "n": None,
    "id": None,
    "p": None,
    "parties": None,
    "client_shares": [],
    "shared_r": None,
    "r": None,
    "multiplicative_share": None,
}

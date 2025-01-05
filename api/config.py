import argparse
from enum import Enum

parser = argparse.ArgumentParser(description="Aukciszek API")
parser.add_argument("--port", type=int, required=True, help="Port number")
args = parser.parse_args()


class STATUS(Enum):
    NOT_INITIALIZED = "Server not initialized"
    INITIALIZED = "Server initialized"
    R_SET = "r is calculated"
    R_SHARED = "r is shared"
    MULT_SHARE_CALCULATED = "Multiplicative share calculated"


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
    "status": STATUS.NOT_INITIALIZED,
}

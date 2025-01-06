from enum import Enum


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
    "client_shares": None,
    "shared_r": None,
    "r": None,
    "multiplicative_share": None,
    "status": STATUS.NOT_INITIALIZED,
}

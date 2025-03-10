from enum import Enum


class STATUS(Enum):
    NOT_INITIALIZED = "Server not initialized"
    INITIALIZED = "Server initialized"
    Q_CALC_SHARED = "Calculated and shared q"
    R_CALC_SHARED = "Calculated and shared r"
    SHARE_CALCULATED = "Share calculated"


state = {
    "t": None,
    "n": None,
    "id": None,
    "p": None,
    "parties": None,
    "client_shares": None,
    "random_number_bit_shares": None,
    "random_number_share": None,
    "zZ": None,
    "posredni-zZ": None,
    "shared_q": None,
    "shared_r": None,
    "calculated_share": None,
    "status": STATUS.NOT_INITIALIZED,
}

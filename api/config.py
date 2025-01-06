from enum import Enum


class STATUS(Enum):
    NOT_INITIALIZED = "Server not initialized"
    INITIALIZED = "Server initialized"
    Q_CALC_SHARED = "Calculated and shared q"
    R_CALC_SHARED = "Calculated and shared r"
    MULT_SHARE_CALCULATED = "Multiplicative share calculated"


state = {
    "t": None,
    "n": None,
    "id": None,
    "p": None,
    "parties": None,
    "client_shares": None,
    "shared_q": None,
    "shared_r": None,
    "multiplicative_share": None,
    "status": STATUS.NOT_INITIALIZED,
}

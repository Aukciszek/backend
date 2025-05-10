from enum import Enum

from decouple import Csv
from decouple import config as dconfig

SECRET_KEYS_JWT = dconfig("SECRET_KEYS_JWT", cast=Csv(str))
TRUSTED_IPS = dconfig("TRUSTED_IPS", cast=Csv(str))
SERVERS = dconfig("SERVERS", cast=Csv(str))
ALGORITHM = dconfig("ALGORITHM", cast=str)
ACCESS_TOKEN_EXPIRE_MINUTES = dconfig("ACCESS_TOKEN_EXPIRE_MINUTES", cast=int)

TEMPORARY_Z0 = 0
TEMPORARY_Z1 = 1


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
    "zZ": None,
    "temporary_zZ": None,
    "xor_multiplication": None,
    "shared_q": None,
    "shared_r": None,
    "calculated_share": None,
    "status": STATUS.NOT_INITIALIZED,
}

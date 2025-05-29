from decouple import Csv
from decouple import config as dconfig

SECRET_KEYS_JWT = dconfig("SECRET_KEYS_JWT", cast=Csv(str))
TRUSTED_IPS = dconfig("TRUSTED_IPS", cast=Csv(str))
SERVERS = dconfig("SERVERS", cast=Csv(str))
ALGORITHM = dconfig("ALGORITHM", cast=str)
ACCESS_TOKEN_EXPIRE_MINUTES = dconfig("ACCESS_TOKEN_EXPIRE_MINUTES", cast=int)


state = {
    # parameters
    "t": None,
    "n": None,
    "id": None,
    "p": None,
    "parties": None,
    # temporary results of arithmetic operations on shares
    "multiplicative_share": None,
    "additive_share": None,
    "xor_share": None,
    # shares
    "shares": {
        "client_shares": None,
        "shared_r": None,
        "shared_q": None,
        "shared_u": None,
    },
    # constant value for multiplication, changes only based on parameters
    "A": None,
    # values used for comparison
    "random_number_bit_shares": [],
    "random_number_share": None,
    "comparison_a": None,
    "z_table": [],
    "Z_table": [],
    "comparison_a_bits": [],
}

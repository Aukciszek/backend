from decouple import Csv
from decouple import config as dconfig

# jwt
SECRET_KEYS_JWT = dconfig("SECRET_KEYS_JWT", cast=Csv(str))
# trusted ips (when not using wireguard)
try:
    TRUSTED_IPS = dconfig("TRUSTED_IPS", cast=Csv(str))
except:
    TRUSTED_IPS = None
# other servers
# when using wireguard - only for client-server communication
# when not using wireguard - for client-server and server-server communication
SERVERS = dconfig("SERVERS", cast=Csv(str))
# optional wireguard configuration
try:
    WIREGUARD_IPS = dconfig("WIREGUARD_IPS", cast=Csv(str))
    WIREGUARD_SERVERS = dconfig("WIREGUARD_SERVERS", cast=Csv(str))
    USING_WIREGUARD = True
except:
    WIREGUARD_IPS = None
    WIREGUARD_SERVERS = None
    USING_WIREGUARD = False
# other required
ALGORITHM = dconfig("ALGORITHM", cast=str)
ACCESS_TOKEN_EXPIRE_MINUTES = dconfig("ACCESS_TOKEN_EXPIRE_MINUTES", cast=int)
SERVER_ID = dconfig("SERVER_ID", cast=int, default=0)


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

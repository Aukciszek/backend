from pydantic import BaseModel


class InitialValuesData(BaseModel):
    id: int
    p: str


class ShareData(BaseModel):
    share: str


class AComparisonData(BaseModel):
    first_client_id: int
    second_client_id: int


class ZComparisonData(BaseModel):
    opened_a: str
    l: int
    k: int


class RData(BaseModel):
    take_value_from_temporary_zZ: bool = False
    zZ_first_multiplication_factor: list[int] | None = None
    zZ_second_multiplication_factor: list[int] | None = None
    calculate_final_comparison_result: bool = False
    opened_a: str | None = None
    l: int | None = None
    k: int | None = None


class CalculateMultiplicativeShareData(BaseModel):
    set_in_temporary_zZ_index: int | None = None
    calculate_for_xor: bool


class XorData(BaseModel):
    take_value_from_temporary_zZ: bool
    zZ_first_multiplication_factor: list[int]
    zZ_second_multiplication_factor: list[int]


class SharedQData(BaseModel):
    party_id: int
    shared_q: str


class SharedRData(BaseModel):
    party_id: int
    shared_r: str


class CalculatedComparisonResultData(BaseModel):
    opened_a: str
    l: int
    k: int


class RegisterData(BaseModel):
    email: str
    password: str
    is_admin: bool


class LoginData(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    server: str


class AuthenticationResponse(BaseModel):
    """
    Response model for the /api/auth/login and /api/auth/register endpoints.
    """

    access_tokens: list[TokenResponse]
    token_type: str


class BiddersResponse(BaseModel):
    """
    Response model for the /api/get-bidders endpoint.
    """

    bidders: list[int]


class ResultResponse(BaseModel):
    """
    Response model for endpoints that simply return a result message.
    """

    result: str


class InitialValuesResponse(BaseModel):
    """
    Response model for the /api/initial-values endpoint.
    """

    t: int
    n: int
    p: str
    parties: list[str]


class CalculatedShareResponse(BaseModel):
    """
    Response model for the /api/return-calculated-share endpoint.
    """

    id: int
    calculated_share: str


class ReconstructedSecretResponse(BaseModel):
    """
    Response model for the /api/reconstruct-secret endpoint.
    """

    secret: str


class StatusResponse(BaseModel):
    """
    Response model for the /api/status endpoint.
    """

    status: str


class TokenData(BaseModel):
    uid: int | None = None
    isAdmin: bool | None = None

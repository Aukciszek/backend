from pydantic import BaseModel


class InitialValuesData(BaseModel):
    id: int
    p: str


class SetClientShareData(BaseModel):
    share: str


class SetShareData(BaseModel):
    share_name: str
    share_value: str


class AComparisonData(BaseModel):
    first_client_id: int
    second_client_id: int
    l: int
    k: int


class ZComparisonData(BaseModel):
    opened_a: str
    l: int
    k: int


class RData(BaseModel):
    first_share_name: str
    second_share_name: str


class AdditiveShareData(BaseModel):
    first_share_name: str
    second_share_name: str


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


class SharedUData(BaseModel):
    """
    Data model for the /api/receive-u-from-parties endpoint.
    """

    party_id: int
    shared_u: str


class PrepareZTablesData(BaseModel):
    """
    Data model for the /api/prepare-z-tables endpoint.
    """

    l: int
    k: int
    opened_a: str


class InitializezAndZZData(BaseModel):
    """
    Data model for the /api/initialize-z-and-Z endpoint.
    """

    l: int


class ShareToReconstruct(BaseModel):
    """
    Data model for the /api/reconstruct-secret and /api/return-calculated-share endpoints.
    """

    share_to_reconstruct: str

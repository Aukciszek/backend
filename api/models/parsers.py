from pydantic import BaseModel, EmailStr


class InitialValuesData(BaseModel):
    """Data model for initial values data."""

    id: int
    p: str


class SetClientShareData(BaseModel):
    """Data model for setting client share data."""

    share: str


class SetShareData(BaseModel):
    """Data model for setting general share data."""

    share_name: str
    share_value: str


class AComparisonData(BaseModel):
    """Data model for comparing two clients."""

    first_client_id: int
    second_client_id: int
    l: int
    k: int


class RData(BaseModel):
    """Data model for R operation shares."""

    first_share_name: str
    second_share_name: str


class AdditiveShareData(BaseModel):
    """Data model for additive share operations."""

    first_share_name: str
    second_share_name: str


class SharedQData(BaseModel):
    """Data model for shared Q values."""

    party_id: int
    shared_q: str


class SharedRData(BaseModel):
    """Data model for shared R values."""

    party_id: int
    shared_r: str


class RegisterData(BaseModel):
    """Data model for registration endpoint."""

    email: EmailStr
    password: str
    is_admin: bool


class LoginData(BaseModel):
    """Data model for login endpoint."""

    email: str
    password: str


class TokenResponse(BaseModel):
    """Response model for token details."""

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


class TokenData(BaseModel):
    """Data model for token payload."""

    uid: int | None = None
    email: str | None = None
    isAdmin: bool | None = None


class SharedUData(BaseModel):
    """Data model for receiving shared U from parties."""

    party_id: int
    shared_u: str


class PrepareZTablesData(BaseModel):
    """Data model for preparing Z tables."""

    l: int
    k: int
    opened_a: str


class InitializezAndZZData(BaseModel):
    """Data model for initializing z and Z entities."""

    l: int


class ShareToReconstruct(BaseModel):
    """Data model for share reconstruction input."""

    share_to_reconstruct: str


class ReconstructSecret(BaseModel):
    """Response model for the /api/reconstruct-secret endpoint."""

    secret: str


class ReturnCalculatedShare(BaseModel):
    """Response model for the /api/return-calculated-share endpoint."""

    id: int
    share_to_reconstruct: str

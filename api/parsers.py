from pydantic import BaseModel


class InitialValues(BaseModel):
    t: int
    n: int
    id: int
    p: str
    parties: list[str]


class ShareData(BaseModel):
    client_id: int
    share: str


class RData(BaseModel):
    first_client_id: int
    second_client_id: int


class SharedQData(BaseModel):
    party_id: int
    shared_q: int


class SharedRData(BaseModel):
    party_id: int
    shared_r: int

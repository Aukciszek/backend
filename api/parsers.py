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


class AComparisonData(BaseModel):
    l: int
    k: int
    first_client_id: int
    second_client_id: int


class ZComparisonData(BaseModel):
    opened_a: int
    l: int
    k: int


class RData(BaseModel):
    take_value_from_temporary_zZ: bool = False
    zZ_first_multiplication_factor: list[int] = None
    zZ_second_multiplication_factor: list[int] = None
    calculate_final_comparison_result: bool = False
    opened_a: int = None
    l: int = None
    k: int = None


class CalculateMultiplicativeShareData(BaseModel):
    set_in_temporary_zZ_index: int = None
    calculate_for_xor: bool


class XorData(BaseModel):
    take_value_from_temporary_zZ: bool
    zZ_first_multiplication_factor: list[int]
    zZ_second_multiplication_factor: list[int]


class SharedQData(BaseModel):
    party_id: int
    shared_q: int


class SharedRData(BaseModel):
    party_id: int
    shared_r: int


class CalculatedComparisonResultData(BaseModel):
    opened_a: int
    l: int
    k: int

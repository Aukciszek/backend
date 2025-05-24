from fastapi import APIRouter, Depends, HTTPException, status

from api.config import state
from api.dependecies.auth import get_current_user
from api.models.parsers import ResultResponse
from api.utils.utils import validate_initialized, validate_initialized_shares

router = APIRouter(
    prefix="/api",
    tags=["XOR"],
)


@router.put(
    "/calculate-xor-share",
    status_code=status.HTTP_201_CREATED,
    summary="Calculate XOR share",
    response_description="XOR share (computed as (additive_share - 2*multiplicative_share) mod p) calculated.",
    response_model=ResultResponse,
    responses={
        201: {
            "description": "XOR share calculated successfully.",
            "content": {
                "application/json": {"example": {"result": "XOR share calculated"}}
            },
        },
        400: {
            "description": "Additive share, multiplicative share, or p is not initialized.",
            "content": {
                "application/json": {
                    "example": {"detail": "additive_share is not initialized."}
                }
            },
        },
        403: {
            "description": "Forbidden. User does not have permission.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "You do not have permission to access this resource."
                    }
                }
            },
        },
    },
)
async def calculate_xor_share(current_user: dict = Depends(get_current_user)):
    """
    Calculates the XOR share using the formula:
        (additive_share - 2 * multiplicative_share) mod p.
    """
    if current_user.get("isAdmin") == False:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access this resource.",
        )

    validate_initialized(["additive_share", "multiplicative_share", "p"])

    state["xor_share"] = (
        state.get("additive_share", 0) - 2 * state.get("multiplicative_share", 0)
    ) % state.get("p", 0)

    return {"result": "XOR share calculated"}


@router.put(
    "/set-xor-share/{share_name}",
    status_code=status.HTTP_201_CREATED,
    summary="Set share from XOR share",
    response_description="Share set using the previously calculated XOR share.",
    response_model=ResultResponse,
    responses={
        201: {
            "description": "Share set from XOR share successfully.",
            "content": {
                "application/json": {
                    "example": {"result": "Share {share_name} set from xor share."}
                }
            },
        },
        400: {
            "description": "XOR share is not initialized.",
            "content": {
                "application/json": {
                    "example": {"detail": "xor_share is not initialized."}
                }
            },
        },
        403: {
            "description": "Forbidden. User does not have permission.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "You do not have permission to access this resource."
                    }
                }
            },
        },
    },
)
async def set_share_from_xor_share(
    share_name: str, current_user: dict = Depends(get_current_user)
):
    """
    Sets the share named {share_name} using the previously calculated XOR share.

    Path Parameters:
    - `share_name`: The name of the share to set
    """
    if current_user.get("isAdmin") == False:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access this resource.",
        )

    validate_initialized(["xor_share"])

    state["shares"][share_name] = state.get("xor_share", 0)

    return {"result": f"Share {share_name} set from xor share."}


@router.put(
    "/set-temporary-random-bit-share/{bit_index}",
    status_code=status.HTTP_201_CREATED,
    summary="Set temporary random bit share",
    response_description="Temporary random bit share set at the specified index using party ID and designated share.",
    response_model=ResultResponse,
    responses={
        201: {
            "description": "Random number bit share set successfully.",
            "content": {
                "application/json": {
                    "example": {
                        "result": "Random number bit share at index {bit_index} set successfully."
                    }
                }
            },
        },
        400: {
            "description": "Server is not initialized or shares are not provided.",
            "content": {
                "application/json": {"example": {"detail": "id is not initialized."}}
            },
        },
        403: {
            "description": "Forbidden. User does not have permission.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "You do not have permission to access this resource."
                    }
                }
            },
        },
    },
)
async def set_random_number_bit_share_to_temporary_random_bit_share(
    bit_index: int, current_user: dict = Depends(get_current_user)
):
    """
    Sets the temporary random bit share at the provided index using the party ID and a designated share.

    Path Parameters:
    - `bit_index`: The index at which to set the random bit share
    """
    if current_user.get("isAdmin") == False:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access this resource.",
        )

    validate_initialized(["id"])
    validate_initialized_shares(["temporary_random_bit"])

    while len(state.get("random_number_bit_shares", [])) < bit_index + 1:
        state["random_number_bit_shares"].append(None)

    state["random_number_bit_shares"][bit_index] = (
        state.get("id", None),
        state.get("shares", {}).get("temporary_random_bit", 0),
    )

    return {"result": f"Random number bit share at index {bit_index} set successfully."}


@router.put(
    "/calculate-share-of-random-number",
    status_code=status.HTTP_201_CREATED,
    summary="Calculate share of random number",
    response_description="Share of random number calculated by multiplying bit shares with powers of 2 and reducing modulo p.",
    response_model=ResultResponse,
    responses={
        201: {
            "description": "Share of random number calculated successfully.",
            "content": {
                "application/json": {
                    "example": {
                        "result": "Share of random number calculated successfully."
                    }
                }
            },
        },
        400: {"description": "Invalid request."},
        403: {
            "description": "Forbidden. User does not have permission.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "You do not have permission to access this resource."
                    }
                }
            },
        },
    },
)
async def calculate_share_of_random_number(
    current_user: dict = Depends(get_current_user),
):
    """
    Calculates the share of the random number by multiplying bit shares with increasing powers of 2
    and reducing modulo p.
    """
    if current_user.get("isAdmin") == False:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access this resource.",
        )

    def multiply_bit_shares_by_powers_of_2(shares):
        multiplied_shares = []
        for i in range(len(shares)):
            multiplied_shares.append((shares[i][0], 2**i * shares[i][1]))
        return multiplied_shares

    def add_multiplied_shares(multiplied_shares):
        party_id = multiplied_shares[0][0]
        value_of_share_r = multiplied_shares[0][1]
        for i in range(1, len(multiplied_shares)):
            value_of_share_r += multiplied_shares[i][1]
        return (
            party_id,
            value_of_share_r % state.get("p", 0),
        )

    pom = multiply_bit_shares_by_powers_of_2(state.get("random_number_bit_shares", []))
    share_of_random_number = add_multiplied_shares(pom)

    state["random_number_share"] = share_of_random_number[1]

    return {
        "result": "Share of random number calculated successfully.",
    }

import asyncio
from typing import Annotated

import aiohttp
from fastapi import APIRouter, Depends, HTTPException, status

from api.config import state
from api.dependecies.auth import get_current_user
from api.models.parsers import (
    AComparisonData,
    InitializezAndZZData,
    PrepareZTablesData,
    ResultResponse,
    TokenData,
)
from api.utils.utils import (
    binary,
    send_post_request,
    validate_initialized,
    validate_initialized_shares,
    validate_initialized_shares_array,
)

router = APIRouter(
    prefix="/api",
    tags=["Comparison"],
)


@router.put(
    "/calculate-a-comparison",
    status_code=status.HTTP_201_CREATED,
    summary="Calculate 'a' for comparison",
    response_description="'a' value computed from client shares and random number share.",
    response_model=ResultResponse,
    responses={
        201: {
            "description": "'a' for comparison calculated successfully.",
            "content": {
                "application/json": {
                    "example": {"result": "'a' for comparison calculated"}
                }
            },
        },
        400: {
            "description": "Invalid input or not enough shares.",
            "content": {
                "application/json": {
                    "examples": {
                        "not_enough_shares": {
                            "value": {
                                "detail": "At least two client shares must be configured."
                            }
                        },
                        "same_client": {
                            "value": {"detail": "Client IDs must be different."}
                        },
                        "missing_shares": {
                            "value": {
                                "detail": "Shares not set for one or both clients."
                            }
                        },
                    }
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
async def calculate_a_comparison(
    values: AComparisonData,
    current_user: Annotated[TokenData, Depends(get_current_user)],
):
    """
    Computes the comparison value 'a' using:
       2^(l+k+1) - random_number_share + 2^l + first_client_share - second_client_share.
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access this resource.",
        )

    validate_initialized(["random_number_share"])
    validate_initialized_shares(["client_shares"])

    if len(state.get("shares", {}).get("client_shares", [])) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least two client shares must be configured.",
        )

    if values.first_client_id == values.second_client_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Client IDs must be different.",
        )

    first_client_share = next(
        (
            y
            for x, y in state.get("shares", {}).get("client_shares", [])
            if x == values.first_client_id
        ),
        None,
    )
    second_client_share = next(
        (
            y
            for x, y in state.get("shares", {}).get("client_shares", [])
            if x == values.second_client_id
        ),
        None,
    )

    if first_client_share is None or second_client_share is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Shares not set for one or both clients.",
        )

    state["shares"]["comparison_a"] = (
        pow(2, values.l + values.k + 1)
        - state.get("random_number_share", 0)
        + pow(2, values.l)
        + first_client_share
        - second_client_share
    )

    return {"result": "'a' for comparison calculated"}


@router.post(
    "/prepare-z-tables",
    status_code=status.HTTP_201_CREATED,
    summary="Prepare Z tables",
    response_description="Z tables prepared using the opened 'a' value and security parameters l and k.",
    response_model=ResultResponse,
    responses={
        201: {
            "description": "Z tables prepared successfully.",
            "content": {
                "application/json": {
                    "example": {"result": "Z tables prepared successfully."}
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
async def prepare_z_tables(
    values: PrepareZTablesData,
    current_user: Annotated[TokenData, Depends(get_current_user)],
):
    """
    Prepares Z tables for the comparison protocol using the opened 'a' value, and security parameters l and k.
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access this resource.",
        )

    a_bin = binary(int(values.opened_a, 16))

    while len(a_bin) < values.l + values.k:
        a_bin.append(0)

    state["comparison_a_bits"] = a_bin

    state["z_table"] = [None for _ in range(values.l)]
    state["Z_table"] = [None for _ in range(values.l)]

    for i in range(values.l - 1, -1, -1):
        state["z_table"][i] = state.get("comparison_a_bits", [])[i]
        state["Z_table"][i] = state.get("comparison_a_bits", [])[i]

    return {
        "result": "Z tables prepared successfully.",
    }


@router.put(
    "/calculate-additive-share-of-z-table/{index}",
    status_code=status.HTTP_201_CREATED,
    summary="Calculate additive share of Z table",
    response_description="Additive share of Z table at the specified index calculated using random bit share.",
    response_model=ResultResponse,
    responses={
        201: {
            "description": "Additive share of Z table calculated successfully.",
            "content": {
                "application/json": {
                    "example": {
                        "result": "Additive share of z table at index {index} calculated successfully."
                    }
                }
            },
        },
        400: {
            "description": "Index out of bounds for comparison_a_bits or random_number_bit_shares.",
            "content": {
                "application/json": {
                    "example": {"detail": "Index out of bounds for comparison_a_bits."}
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
async def calculate_additive_share_of_z_table_arguments(
    index: int, current_user: Annotated[TokenData, Depends(get_current_user)]
):
    """
    Calculates an additive share from the Z table at the given index using a random bit share.
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access this resource.",
        )

    validate_initialized(["p"])

    if index < 0 or index >= len(state.get("comparison_a_bits", [])):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Index out of bounds for comparison_a_bits.",
        )
    if index >= len(state.get("random_number_bit_shares", [])):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Index out of bounds for random_number_bit_shares.",
        )

    first_share = state.get("comparison_a_bits", [])[index]
    second_share = state.get("random_number_bit_shares", [])[index]

    state["additive_share"] = (first_share + second_share) % state.get("p", 0)

    return {
        "result": f"Additive share of z table at index {index} calculated successfully."
    }


@router.put(
    "/calculate-r-of-z-table/{index}",
    status_code=status.HTTP_201_CREATED,
    summary="Calculate r for Z table",
    response_description="R value for the multiplication of the Z table at the specified index calculated and distributed.",
    response_model=ResultResponse,
    responses={
        201: {
            "description": "R for multiplication of Z table calculated and shared successfully.",
            "content": {
                "application/json": {
                    "example": {
                        "result": "R for multiplication of z table at index {index} calculated and shared"
                    }
                }
            },
        },
        400: {
            "description": "Invalid share names provided.",
            "content": {
                "application/json": {
                    "example": {"detail": "Invalid share names provided."}
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
async def calculate_r_of_z_table(
    index: int, current_user: Annotated[TokenData, Depends(get_current_user)]
):
    """
    Calculates r for the multiplication of the Z table at the specified index and distributes it.
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access this resource.",
        )

    validate_initialized(["p", "A", "n", "id"])
    validate_initialized_shares_array(["shared_q"])

    if index < 0 or index >= len(state.get("comparison_a_bits", [])):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Index out of bounds for comparison_a_bits.",
        )
    if index >= len(state.get("random_number_bit_shares", [])):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Index out of bounds for random_number_bit_shares.",
        )

    first_share = state.get("comparison_a_bits", [])[index]
    second_share = state.get("random_number_bit_shares", [])[index]

    if first_share is None or second_share is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid share names provided.",
        )

    qs = [x for x in state.get("shares", {}).get("shared_q", [])]

    multiplied_shares = ((first_share * second_share) + sum(qs)) % state.get("p", 0)

    r = [
        (multiplied_shares * state.get("A", 0)[state.get("id", 0) - 1][i])
        % state.get("p", 0)
        for i in range(state.get("n", 0))
    ]

    # Distribute r values to other parties
    async with aiohttp.ClientSession() as session:
        tasks = []
        for i in range(state.get("n", 0)):
            if i == state.get("id", 0) - 1:
                state["shares"]["shared_r"][i] = r[i]
                continue

            url = f"{state['parties'][i]}/api/receive-r-from-parties"
            json_data = {"party_id": state.get("id", None), "shared_r": hex(r[i])}
            tasks.append(send_post_request(session, url, json_data))

        await asyncio.gather(*tasks)

        return {
            "result": f"R for multipication of z table at index {index} calculated and shared"
        }


@router.put(
    "/set-z-table-to-xor-share/{index}",
    status_code=status.HTTP_201_CREATED,
    summary="Set Z table to XOR share",
    response_description="Z table entry at the specified index set to the pre-computed XOR share.",
    response_model=ResultResponse,
    responses={
        201: {
            "description": "Z table at index set to XOR share successfully.",
            "content": {
                "application/json": {
                    "example": {
                        "result": "z table at index {index} set to XOR share successfully."
                    }
                }
            },
        },
        400: {
            "description": "Index out of bounds for z_table.",
            "content": {
                "application/json": {
                    "example": {"detail": "Index out of bounds for z_table."}
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
async def set_z_table_to_xor_share(
    index: int, current_user: Annotated[TokenData, Depends(get_current_user)]
):
    """
    Sets the Z table entry at the given index equal to the pre-computed XOR share.
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access this resource.",
        )

    validate_initialized(["xor_share"])

    if index < 0 or index >= len(state.get("z_table", [])):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Index out of bounds for z_table.",
        )

    state["z_table"][index] = state.get("xor_share", 0)

    return {"result": f"z table at index {index} set to XOR share successfully."}


@router.post(
    "/initialize-z-and-Z",
    status_code=status.HTTP_201_CREATED,
    summary="Initialize shares z and Z",
    response_description="Shares z and Z initialized from the Z tables based on the security parameter l.",
    response_model=ResultResponse,
    responses={
        201: {
            "description": "Shares z and Z initialized successfully.",
            "content": {
                "application/json": {
                    "example": {"result": "Shares z and Z initialized successfully."}
                }
            },
        },
        400: {
            "description": "Invalid value for l. It must be between 1 and the length of z_table or Z_table.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Invalid value for l. It must be between 1 and the length of z_table."
                    }
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
async def initialize_z_and_Z(
    values: InitializezAndZZData,
    current_user: Annotated[TokenData, Depends(get_current_user)],
):
    """
    Initializes the share values z and Z from the Z tables based on the security parameter l.
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access this resource.",
        )

    if values.l < 1 or values.l > len(state.get("z_table", [])):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid value for l. It must be between 1 and the length of z_table.",
        )
    if values.l > len(state.get("Z_table", [])):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid value for l. It must be between 1 and the length of Z_table.",
        )

    state["shares"]["z"] = state.get("z_table", [])[values.l - 1]
    state["shares"]["Z"] = state.get("Z_table", [])[values.l - 1]

    return {
        "result": "Shares z and Z initialized successfully.",
    }


@router.put(
    "/prepare-for-next-romb/{index}",
    status_code=status.HTTP_201_CREATED,
    summary="Prepare for next romb",
    response_description="Shares x, X, y, Y reset for the next operation round (romb).",
    response_model=ResultResponse,
    responses={
        201: {
            "description": "Prepared for next romb successfully.",
            "content": {
                "application/json": {
                    "example": {"result": "Prepared for next romb with index {index}."}
                }
            },
        },
        400: {
            "description": "Index out of bounds for z_table or Z_table.",
            "content": {
                "application/json": {
                    "example": {"detail": "Index out of bounds for z_table."}
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
async def prepare_for_next_romb(
    index: int, current_user: Annotated[TokenData, Depends(get_current_user)]
):
    """
    Prepares for the next operation round (romb) by resetting share variables x, X, y, Y.
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access this resource.",
        )

    validate_initialized_shares(["z", "Z"])

    if index > len(state.get("z_table", [])):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Index out of bounds for z_table.",
        )
    if index > len(state.get("Z_table", [])):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Index out of bounds for Z_table.",
        )

    state["shares"]["x"] = state.get("shares", {}).get("z", 0)
    state["shares"]["X"] = state.get("shares", {}).get("Z", 0)

    if index == 0:
        state["shares"]["y"] = 0
        state["shares"]["Y"] = 0
    else:
        state["shares"]["y"] = state.get("z_table", [])[index - 1]
        state["shares"]["Y"] = state.get("Z_table", [])[index - 1]

    return {
        "result": f"Prepared for next romb with index {index}. Shares x, X, y, Y set."
    }


@router.put(
    "/prepare-shares-for-res-xors/{comparison_a_bit_index}/{random_number_bit_share_index}",
    status_code=status.HTTP_201_CREATED,
    summary="Prepare shares for res xors",
    response_description="Shares for res xors prepared using comparison_a bit and random number bit share.",
    response_model=ResultResponse,
    responses={
        201: {
            "description": "Shares for res xors prepared successfully.",
            "content": {
                "application/json": {
                    "example": {"result": "Shares for res xors prepared successfully."}
                }
            },
        },
        400: {
            "description": "Invalid comparison_a_bit_index or random_number_bit_share_index.",
            "content": {
                "application/json": {
                    "example": {"detail": "Invalid comparison_a_bit_index."}
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
async def prepare_shares_for_res_xors(
    comparison_a_bit_index: int,
    random_number_bit_share_index: int,
    current_user: Annotated[TokenData, Depends(get_current_user)],
):
    """
    Prepares the shares required for a res xors operation by selecting the bit from comparison_a and
    the corresponding random number bit share.
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access this resource.",
        )

    if comparison_a_bit_index < 0 or comparison_a_bit_index >= len(
        state.get("comparison_a_bits", [])
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid comparison_a_bit_index.",
        )
    if random_number_bit_share_index < 0 or random_number_bit_share_index >= len(
        state.get("random_number_bit_shares", [])
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid random_number_bit_share_index.",
        )

    state["shares"]["a_l"] = state.get("comparison_a_bits", [])[comparison_a_bit_index]
    state["shares"]["r_l"] = state.get("random_number_bit_shares", [])[
        random_number_bit_share_index
    ]

    return {"result": "Shares for res xors prepared successfully."}

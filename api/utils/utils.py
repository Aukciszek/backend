import copy
import os

import aiohttp
from fastapi import HTTPException

from api.config import state


def validate_not_initialized(required_keys):
    for key in required_keys:
        if state[key] is not None:
            raise HTTPException(status_code=400, detail=f"{key} is initialized.")


def validate_initialized(required_keys):
    for key in required_keys:
        if state[key] is None:
            raise HTTPException(status_code=400, detail=f"{key} is not initialized.")


def validate_initialized_shares(required_keys):
    if state["shares"] is None:
        raise HTTPException(status_code=400, detail="shares is not initialized.")
    for key in required_keys:
        if key not in state["shares"]:
            raise HTTPException(
                status_code=400, detail=f"['shares'] does not contain {key}."
            )

        if state["shares"][key] is None:
            raise HTTPException(
                status_code=400, detail=f"['shares']{key} is not initialized."
            )


def validate_initialized_shares_array(required_keys):
    for key in required_keys:
        if key not in state["shares"]:
            raise HTTPException(
                status_code=400, detail=f"['shares'] does not contain {key}."
            )

        if state["shares"][key] is None:
            raise HTTPException(
                status_code=400, detail=f"['shares']{key} is not initialized."
            )

        if not isinstance(state["shares"][key], list):
            raise HTTPException(
                status_code=400,
                detail=f"The element at ['shares']{key} is not a list.",
            )

        for i, value in enumerate(state["shares"][key]):
            if value is None:
                raise HTTPException(
                    status_code=400,
                    detail=f"The element at '['shares']{key}[{i}]' is not initialized.",
                )


async def send_post_request(session, url, json_data=None, headers=None):
    """Send a POST request asynchronously."""
    try:
        async with session.post(url, json=json_data, headers=headers) as response:
            message = await response.json()

            if response.status != 201:
                raise HTTPException(
                    status_code=response.status,
                    detail=f"Failed POST request to {url}: {message}",
                )

            return message
    except aiohttp.ClientError as e:
        raise HTTPException(
            status_code=400, detail=f"HTTP error occurred for {url}: {e}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=400, detail=f"Unexpected error occurred for {url}: {e}"
        )


async def send_get_request(session, url, params=None, headers=None):
    """Send a GET request asynchronously."""
    try:
        async with session.get(url, params=params, headers=headers) as response:
            message = await response.json()

            if response.status != 200:
                raise HTTPException(
                    status_code=response.status,
                    detail=f"Failed GET request to {url}: {message}",
                )

            return message
    except aiohttp.ClientError as e:
        raise HTTPException(
            status_code=400, detail=f"HTTP error occurred for {url}: {e}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=400, detail=f"Unexpected error occurred for {url}: {e}"
        )


binary_internal = lambda n: n > 0 and [n & 1] + binary_internal(n >> 1) or []


def binary(n):
    if n == 0:
        return [0]
    else:
        return binary_internal(n)


def binary_exponentiation(b, k, n):
    if k < 0:
        k = n - 2

    a = 1
    while k:
        if k & 1:
            a = (a * b) % n
        b = (b * b) % n
        k >>= 1
    return a


def modular_multiplicative_inverse(b: int, n: int) -> int:
    A = n
    B = b
    U = 0
    V = 1
    while B != 0:
        q = A // B
        A, B = B, A - q * B
        U, V = V, U - q * V
    if U < 0:
        return U + n
    return U


def inverse_matrix_mod(matrix_dc, modulus):
    matrix_dc = copy.deepcopy(matrix_dc)

    n = len(matrix_dc)
    identity_matrix = [[1 if i == j else 0 for j in range(n)] for i in range(n)]

    for i in range(n):
        # Find the first non-zero element in column i starting from row i
        non_zero_index = next(
            (k for k in range(i, n) if matrix_dc[k][i] % modulus != 0), -1
        )
        if non_zero_index == -1:
            raise HTTPException(
                status_code=400,
                detail="Matrix is not invertible mod p.",
            )

        # Swap rows i and non_zero_index in both matrix and identity_matrix
        matrix_dc[i], matrix_dc[non_zero_index] = (
            matrix_dc[non_zero_index],
            matrix_dc[i],
        )
        identity_matrix[i], identity_matrix[non_zero_index] = (
            identity_matrix[non_zero_index],
            identity_matrix[i],
        )

        # Normalize the pivot row
        pivot = matrix_dc[i][i] % modulus
        pivot_inv = modular_multiplicative_inverse(pivot, modulus)

        matrix_dc[i] = [(x * pivot_inv) % modulus for x in matrix_dc[i]]
        identity_matrix[i] = [(x * pivot_inv) % modulus for x in identity_matrix[i]]

        # Eliminate entries below the pivot
        for j in range(i + 1, n):
            if matrix_dc[j][i] % modulus != 0:
                factor = matrix_dc[j][i]
                matrix_dc[j] = [
                    (matrix_dc[j][k] - factor * matrix_dc[i][k]) % modulus
                    for k in range(n)
                ]
                identity_matrix[j] = [
                    (identity_matrix[j][k] - factor * identity_matrix[i][k]) % modulus
                    for k in range(n)
                ]

    # Back substitution to eliminate entries above the pivots
    for i in range(n - 1, -1, -1):
        for j in range(i - 1, -1, -1):
            if matrix_dc[j][i] % modulus != 0:
                factor = matrix_dc[j][i]
                matrix_dc[j] = [
                    (matrix_dc[j][k] - factor * matrix_dc[i][k]) % modulus
                    for k in range(n)
                ]
                identity_matrix[j] = [
                    (identity_matrix[j][k] - factor * identity_matrix[i][k]) % modulus
                    for k in range(n)
                ]

    return identity_matrix


def multiply_matrix(matrix1, matrix2, modulus):
    n = len(matrix1)
    m = len(matrix2[0])
    l = len(matrix2)

    if len(matrix1[0]) != l:
        raise HTTPException(
            status_code=400,
            detail="Matrix dimensions do not match for multiplication.",
        )

    result = [[0 for _ in range(m)] for _ in range(n)]

    for i in range(n):
        for j in range(m):
            result[i][j] = (
                sum(matrix1[i][k] * matrix2[k][j] % modulus for k in range(l)) % modulus
            )

    return result


def computate_coefficients(shares, p):
    coefficients = []

    for i, (x_i, _) in enumerate(shares):
        li = 1
        for j, (x_j, _) in enumerate(shares):
            if i != j:
                li *= x_j * binary_exponentiation(x_j - x_i, -1, p)
                li %= p
        coefficients.append(li)

    return coefficients


def reconstruct_secret(shares, coefficients, p):
    secret = 0

    for i, (_, y_i) in enumerate(shares):
        secret += y_i * coefficients[i]
        secret %= p

    return secret


def secure_randint(start, end):
    """Generate a secure random integer between start and end (inclusive) using os.urandom."""
    if start > end:
        raise HTTPException(
            status_code=400,
            detail="Start value must be less than or equal to end value.",
        )

    range_size = end - start + 1
    num_bytes = (range_size - 1).bit_length() // 8 + 1
    mask = (1 << (num_bytes * 8)) - 1

    while True:
        random_int = int.from_bytes(os.urandom(num_bytes), "big") & mask
        if random_int < range_size:
            return start + random_int


def f(x, coefficients, p, t):
    return sum([coefficients[i] * x**i for i in range(t)]) % p


def Shamir(t, n, k0, p):
    coefficients = [secure_randint(0, p - 1) for _ in range(t)]
    coefficients[0] = k0

    if coefficients[-1] == 0:
        coefficients[-1] = secure_randint(1, p - 1)

    shares = []

    for i in range(1, n + 1):
        shares.append((i, f(i, coefficients, p, t)))

    return shares

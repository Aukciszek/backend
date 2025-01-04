import copy


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
            raise ValueError("Matrix is not invertible under this modulus.")

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
        raise ValueError("Matrix dimensions do not match.")

    result = [[0 for _ in range(m)] for _ in range(n)]

    for i in range(n):
        for j in range(m):
            result[i][j] = (
                sum(matrix1[i][k] * matrix2[k][j] % modulus for k in range(l)) % modulus
            )

    return result
